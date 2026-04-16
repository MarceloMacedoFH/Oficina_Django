/**
 * Oficina Master - Lógica de Gestão de Ordens de Serviço
 * Versão Final: 100% Funcional
 */

document.addEventListener('DOMContentLoaded', function() {

    // Auxiliar para obter o Token CSRF do Django
    const obterTokenCSRF = () => {
        return window.CSRF_TOKEN || 
               document.querySelector('[name=csrfmiddlewaretoken]')?.value || 
               document.cookie.match(/csrftoken=([\w-]+)/)?.[1];
    };

    // --- 1. BUSCA DE PREÇO E VALIDAÇÃO DE STOCK ---
    document.addEventListener('change', function(evento) {
        if (evento.target.classList.contains('item-select')) {
            const linha = evento.target.closest('tr');
            const tipo = evento.target.dataset.tipo; 
            const id = evento.target.value;

            if (id) {
                fetch(`/ordens/buscar-preco/?tipo=${tipo}&id=${id}`)
                    .then(res => res.json())
                    .then(dados => {
                        const campoPreco = linha.querySelector('.item-price');
                        const campoQtd = linha.querySelector('.item-qty');
                        
                        if (campoPreco) {
                            campoPreco.value = dados.preco.toFixed(2);
                            
                            if (tipo === 'peca') {
                                campoQtd.setAttribute('max', dados.estoque);
                                
                                // Validação de Stock Zerado
                                if (dados.estoque <= 0) {
                                    alert('⚠️ STOCK INDISPONÍVEL: Esta peça não possui saldo.');
                                    evento.target.value = ''; 
                                    if (campoQtd) campoQtd.value = '';
                                    const sub = linha.querySelector('.item-subtotal');
                                    if (sub) sub.value = 'R$ 0,00';
                                    atualizarTotalGeral();
                                    return;
                                }
                            }
                            if (!campoQtd.value || campoQtd.value == 0) campoQtd.value = 1;
                            calcularSubtotalLinha(linha);
                        }
                    })
                    .catch(err => console.error('Erro na busca de dados:', err));
            }
        }

        // Gatilho para recálculo se quantidade ou preço unitário mudar manualmente
        if (evento.target.classList.contains('item-qty') || evento.target.classList.contains('item-price')) {
            const linha = evento.target.closest('tr');
            
            // Validação de limite de stock (apenas para peças)
            if (evento.target.classList.contains('item-qty')) {
                const max = parseFloat(evento.target.getAttribute('max'));
                if (!isNaN(max) && parseFloat(evento.target.value) > max) {
                    alert(`⚠️ Saldo insuficiente! Stock atual: ${max}`);
                    evento.target.value = max;
                }
            }
            
            calcularSubtotalLinha(linha);
        }
    });

    // --- 2. FUNÇÕES DE CÁLCULO ---
    function calcularSubtotalLinha(linha) {
        const campoQtd = linha.querySelector('.item-qty');
        const campoPreco = linha.querySelector('.item-price');
        const campoSubtotal = linha.querySelector('.item-subtotal');
        
        const qtd = parseFloat(campoQtd?.value) || 0;
        const preco = parseFloat(campoPreco?.value) || 0;
        
        const subtotal = qtd * preco;
        if (campoSubtotal) {
            campoSubtotal.value = subtotal.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
        }
        atualizarTotalGeral();
    }

    function atualizarTotalGeral() {
        let somaTotal = 0;
        
        document.querySelectorAll('.item-subtotal').forEach(campo => {
            // Remove R$, pontos de milhar e converte vírgula em ponto para somar
            let valorTexto = campo.value || "0";
            let valorLimpo = valorTexto.replace(/[^\d,.-]/g, '').replace('.', '').replace(',', '.');
            somaTotal += parseFloat(valorLimpo) || 0;
        });

        const visorTotal = document.getElementById('total-geral');
        if (visorTotal) {
            const formatado = somaTotal.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
            if (visorTotal.tagName === 'INPUT') {
                visorTotal.value = formatado;
            } else {
                visorTotal.innerText = formatado;
            }
        }
    }

    // --- 3. GESTÃO DE FORMSETS (ADICIONAR LINHAS) ---
    document.querySelectorAll('.add-row').forEach(botao => {
        botao.addEventListener('click', function() {
            const prefixo = this.dataset.prefix;
            const inputTotalForms = document.getElementById(`id_${prefixo}-TOTAL_FORMS`);
            const novoIndice = parseInt(inputTotalForms.value);
            const corpoTabela = document.querySelector(`#table-${prefixo} tbody`);
            
            const templateOriginal = corpoTabela.querySelector('.form-row');
            const novaLinha = templateOriginal.cloneNode(true);
            
            // Atualiza os nomes e IDs dos campos para o novo índice (Django requirement)
            novaLinha.innerHTML = novaLinha.innerHTML.replace(new RegExp(`${prefixo}-0-`, 'g'), `${prefixo}-${novoIndice}-`);
            
            // Limpa os valores da nova linha
            novaLinha.querySelectorAll('input, select').forEach(campo => {
                campo.value = '';
                if (campo.classList.contains('item-subtotal')) campo.value = 'R$ 0,00';
                campo.removeAttribute('max'); // Será definido no evento 'change'
            });
            
            corpoTabela.appendChild(novaLinha);
            inputTotalForms.value = novoIndice + 1;
        });
    });

    // --- 4. ALTERAÇÃO DE STATUS (LISTAGEM) ---
    document.addEventListener('click', function(e) {
        // O segredo está aqui: .closest() sobe na hierarquia até encontrar o botão
        const btn = e.target.closest('.btn-status');
        
        // Se o clique foi no botão ou em qualquer coisa dentro dele (como o ícone)
        if (btn) {
            e.preventDefault();
            const osId = btn.dataset.os;
            const novoStatus = btn.dataset.status;

            if (confirm(`Deseja alterar o status da OS #${osId} para ${novoStatus}?`)) {
                const formDados = new FormData();
                formDados.append('status', novoStatus);
                formDados.append('csrfmiddlewaretoken', obterTokenCSRF());

                fetch(`/ordens/alterar-status/${osId}/`, {
                    method: 'POST',
                    body: formDados,
                    headers: { 'X-Requested-With': 'XMLHttpRequest' }
                })
                .then(async response => {
                    const data = await response.json();
                    if (!response.ok) throw new Error(data.message);
                    window.location.reload(); // Recarrega para atualizar a cor do badge
                })
                .catch(erro => {
                    alert(`❌ OPERAÇÃO RECUSADA: ${erro.message}`);
                });
            }
        }
    });
});