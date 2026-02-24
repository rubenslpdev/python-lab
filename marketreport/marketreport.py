import os
import json
import requests
import yfinance as yf
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def ler_configuracoes(filepath="config.json"):
    """Lê a lista de ativos do arquivo JSON."""
    with open(filepath, "r", encoding="utf-8") as file:
        return json.load(file)

def buscar_dados_ativo(ticker_symbol):
    """Busca os dados do ativo no yfinance e faz os cálculos."""
    try:
        ativo = yf.Ticker(ticker_symbol)
        
        # Puxa 2 meses de histórico para garantir que tenhamos 20 dias úteis para a SMA
        hist = ativo.history(period="2mo")
        
        if hist.empty:
            return None

        # Preço Atual (último fechamento)
        preco_atual = hist['Close'].iloc[-1]

        # Mínimo e Máximo dos últimos 7 pregões/dias
        ultimos_7_dias = hist.tail(7)
        min_7d = ultimos_7_dias['Low'].min()
        max_7d = ultimos_7_dias['High'].max()

        # SMA de 20 períodos (Média Móvel Simples de 20 dias)
        sma_20 = hist['Close'].rolling(window=20).mean().iloc[-1]

        # Lógica de Tendência
        if preco_atual > sma_20:
            tendencia = "Alta 📈"
        elif preco_atual < sma_20:
            tendencia = "Baixa 📉"
        else:
            tendencia = "Neutra ➖"

        return {
            "ticker": ticker_symbol,
            "preco": preco_atual,
            "min_7d": min_7d,
            "max_7d": max_7d,
            "tendencia": tendencia
        }

    except Exception as e:
        print(f"Erro ao buscar dados de {ticker_symbol}: {e}")
        return None

def enviar_mensagem_telegram(mensagem):
    """Envia a mensagem montada para o bot do Telegram usando requests."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Erro: TELEGRAM_TOKEN ou TELEGRAM_CHAT_ID não encontrados no .env")
        return
    
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mensagem,
        "parse_mode": "HTML" # Permite usar negrito <b> no telegram
    }
    
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        print("Relatório enviado com sucesso via Telegram!")
    else:
        print(f"Falha ao enviar: {response.status_code} - {response.text}")

def gerar_relatorio():
    """Lê o config, busca os dados e formata a mensagem."""
    config = ler_configuracoes()
    stocks = config["ativos"]["stocks"]
    criptos = config["ativos"]["criptos"]

    linhas_relatorio = ["📊 <b>Relatório Semanal de Ativos</b>\n"]

    # Processar Ações Brasileiras (B3)
    linhas_relatorio.append("🏢 <b>Ações (B3) e Índice</b>")
    for item in stocks:
        symbol = item["ticker"]
        dados = buscar_dados_ativo(symbol)
        if dados:
            # Formatação especial para BRL (R$)
            nome_amigavel = symbol.replace('.SA', '') # Remove o .SA pra ficar mais bonito
            linhas_relatorio.append(
                f"🔸 <b>{nome_amigavel}</b>: R$ {dados['preco']:.2f} | {dados['tendencia']}\n"
                f"   └ <i>Min: R$ {dados['min_7d']:.2f} / Max: R$ {dados['max_7d']:.2f}</i>"
            )

    linhas_relatorio.append("\n🪙 <b>Criptomoedas</b>")
    # Processar Criptomoedas
    for item in criptos:
        symbol = item["ticker"]
        dados = buscar_dados_ativo(symbol)
        if dados:
            # Formatação especial para USD ($)
            linhas_relatorio.append(
                f"🔸 <b>{symbol}</b>: $ {dados['preco']:,.2f} | {dados['tendencia']}\n"
                f"   └ <i>Min: $ {dados['min_7d']:,.2f} / Max: $ {dados['max_7d']:,.2f}</i>"
            )

    # Junta tudo e envia
    mensagem_final = "\n".join(linhas_relatorio)
    enviar_mensagem_telegram(mensagem_final)

if __name__ == "__main__":
    gerar_relatorio()
