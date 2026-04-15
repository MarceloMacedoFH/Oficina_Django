/**
 * Oficina Master - Lógica de Gestão de Ordens de Serviço
 * Versão Final: 100% Funcional
 */

document.addEventListener('DOMContentLoaded', function() {

    // Auxiliar para obter o Token CSRF do Django
    const obterTokenCSRF = () => {
        return window.CSRF_TOKEN || document.querySelector('[name=csrfmiddlewaretoken]')?.value;
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
                        const campoSelect = evento.target;

                        if (campoPreco) {
                            campoPreco.value = dados.preco.toFixed(2);
                            
                            if (tipo === 'peca') {
                                campoQtd.setAttribute('max', dados.estoque);
                                
                                // Validação de Stock Zerado
                                if (dados.estoque <= 0) {
                                    alert('⚠️ ESTOQUE INDISPONÍVEL: Esta peça não possui saldo para venda.');
                                    
                                    // Reset total da linha
                                    campoSelect.value = ''; 
                                    campoQtd.value = '';
                                    campoPreco.value = '';
                                    const sub = linha.querySelector('.item-subtotal');
                                    if (sub) sub.value = 'R$ 0,00';
                                    
                                    atualizarTotalGeral();
                                    return;
                                }
                                if (!campoQtd.value || campoQtd.value == 0) campoQtd.value = 1;
                            } else {
                                // Para serviços, apenas garante quantidade 1
                                if (!campoQtd.value || campoQtd.value == 0) campoQtd.value = 1;
                            }
                            calcularSubtotalLinha(linha);
                        }
                    })
                    .catch(err => console.error('Erro na busca de dados:', err));
            }
        }

        // Validação de quantidade manual
        if (evento.target.classList.contains('item-qty')) {
            const linha = evento.target.closest('tr');
            const campoQtd = evento.target;
            const max = parseFloat(campoQtd.getAttribute('max'));

            if (!isNaN(max) && parseFloat(campoQtd.value) > max) {
                alert(`⚠️ Saldo insuficiente! O estoque atual é de ${max} unidades.`);
                campoQtd.value = max;
            }
            calcularSubtotalLinha(linha);
        }
    });

    // --- 2. FUNÇÕES DE CÁLCULO ---
    function calcularSubtotalLinha(linha) {
        const campoQtd = linha.querySelector('.item-qty');
        const campoPreco = linha.querySelector('.item-price');
        
        // Verifica se há valores válidos antes de calcular
        if (!campoQtd.value || !campoPreco.value || parseFloat(campoQtd.value) <= 0) {
            const sub = linha.querySelector('.item-subtotal');
            if (sub) sub.value = 'R$ 0,00';
            atualizarTotalGeral();
            return;
        }

        const qtd = parseFloat(campoQtd.value) || 0;
        const preco = parseFloat(campoPreco.value) || 0;
        const campoSubtotal = linha.querySelector('.item-subtotal');
        
        const subtotal = qtd * preco;
        if (campoSubtotal) {
            campoSubtotal.value = subtotal.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
        }
        atualizarTotalGeral();
    }

    function atualizarTotalGeral() {
        let somaTotal = 0;
        
        document.querySelectorAll('.item-subtotal').forEach(campo => {
            // Remove R$, pontos de milhar e converte vírgula em ponto
            let valorTexto = campo.value || "0";
            let valorLimpo = valorTexto.replace(/[^\d,.-]/g, '').replace('.', '').replace(',', '.');
            somaTotal += parseFloat(valorLimpo) || 0;
        });

        const visorTotal = document.getElementById('total-geral');
        if (visorTotal) {
            const formatado = somaTotal.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
            // Atualiza seja um input ou um elemento de texto (span/div)
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
            
            const templateOriginal = corpoTabela.querySelectorAll('.form-row')[0];
            const novaLinha = templateOriginal.cloneNode(true);
            
            // Atualiza os índices do Django (ex: pecas-0- virá pecas-1-)
            novaLinha.innerHTML = novaLinha.innerHTML.replace(new RegExp(`${prefixo}-0-`, 'g'), `${prefixo}-${novoIndice}-`);
            
            // Limpa os campos da nova linha
            novaLinha.querySelectorAll('input, select').forEach(campo => {
                campo.value = '';
                if (campo.classList.contains('item-subtotal')) campo.value = 'R$ 0,00';
                // Remove o atributo max da nova linha para ser definido no 'change'
                campo.removeAttribute('max');
            });
            
            corpoTabela.appendChild(novaLinha);
            inputTotalForms.value = novoIndice + 1;
        });
    });

    // --- 4. ALTERAÇÃO DE STATUS (LISTAGEM) ---
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('btn-status')) {
            e.preventDefault();
            const osId = e.target.dataset.os;
            const novoStatus = e.target.dataset.status;

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
                return data;
            })
            .then(() => {
                window.location.reload();
            })
            .catch(erro => {
                alert(`❌ OPERAÇÃO RECUSADA: ${erro.message}`);
            });
        }
    });
});