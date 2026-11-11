import { useEffect, useRef, useState } from 'react'
import StockChart from './StockChart'
import snapshot from './ibmSnapshot.json'
import './App.css'

const companies = {
  IBM: 'International Business Machines',
  AAPL: 'Apple',
  MSFT: 'Microsoft',
}

const prompts = [
  { mark: '≡', label: 'Earnings & valuation', question: symbol => `Show ${symbol} earnings and valuation` },
  { mark: '↔', label: 'Compare stocks', question: () => 'Compare IBM and MSFT' },
  { mark: '↗', label: 'Price projection', question: symbol => `Project ${symbol} over 3 years` },
  { mark: '%', label: 'What-if scenario', question: () => 'What if $1,000 drops 10%?' },
]

const ranges = { '1W': 5, '1M': 22, '2M': 45 }
const snapshotSource = 'Alpha Vantage · saved snapshot'
const formatPrice = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' })
const formatVolume = new Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 2 })

function formatDate(value) {
  return new Intl.DateTimeFormat('en-US', {
    month: 'short', day: 'numeric', year: 'numeric', timeZone: 'UTC',
  }).format(new Date(value + 'T00:00:00Z'))
}

async function request(path, options) {
  const response = await fetch(path, options)
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new Error(typeof body.detail === 'string' ? body.detail : 'The assistant is unavailable. Try again.')
  }
  return response.json()
}

function Result({ data }) {
  return (
    <article className="response">
      <p>{data.answer}</p>
      {data.table && (
        <div className="table-scroll" tabIndex={0} aria-label="Analysis results">
          <table>
            <thead><tr>{data.table.columns.map(column => <th key={column} scope="col">{column}</th>)}</tr></thead>
            <tbody>{data.table.rows.map((row, i) => (
              <tr key={i}>{row.map((cell, j) => <td key={j}>{typeof cell === 'number' ? cell.toLocaleString('en-US', { maximumFractionDigits: 4 }) : cell ?? 'Unavailable'}</td>)}</tr>
            ))}</tbody>
          </table>
        </div>
      )}
      {!!data.sources?.length && <p className="detail"><strong>Sources</strong> {data.sources.join(' · ')}</p>}
      {!!data.assumptions?.length && <p className="detail"><strong>Assumptions</strong> {data.assumptions.join(' ')}</p>}
    </article>
  )
}

function PromptButtons({ symbol, busy, submit, compact = false }) {
  return (
    <div className={compact ? 'prompts prompt-strip' : 'prompts'} aria-label="Suggested analyses">
      {prompts.map(prompt => (
        <button type="button" key={prompt.label} disabled={busy} onClick={() => submit(prompt.question(symbol))}>
          <span className="prompt-mark" aria-hidden="true">{prompt.mark}</span>
          <span>{prompt.label}</span>
          <span className="prompt-arrow" aria-hidden="true">↗</span>
        </button>
      ))}
    </div>
  )
}

function MarketPanel({ market, range, setRange, refresh, marketProgress, marketError, busy }) {
  const { chart, source } = market
  const { candles, symbol, currency } = chart
  const ordered = [...candles].sort((a, b) => a.date.localeCompare(b.date))
  const latest = ordered.at(-1)
  const previous = ordered.at(-2)
  const change = previous?.close ? (latest.close / previous.close - 1) * 100 : null
  const changeClass = change > 0 ? 'positive' : change < 0 ? 'negative' : ''
  const recent = ordered.slice(-10)
  const average = recent.length === 10 ? recent.reduce((sum, day) => sum + day.close, 0) / 10 : null

  return (
    <section className="panel market-panel" aria-labelledby="market-title">
      <header className="market-header">
        <div className="market-identity">
          <span className="ticker-mark" aria-hidden="true">{symbol}</span>
          <div>
            <h2 id="market-title">{companies[symbol] ?? symbol}</h2>
            <p>{symbol} <span aria-hidden="true">/</span> {currency} <span aria-hidden="true">/</span> Daily</p>
          </div>
        </div>
        <button type="button" className="refresh" onClick={refresh} disabled={busy}>
          <span aria-hidden="true">↻</span> Refresh
        </button>
      </header>

      <div className="market-quote">
        <div className="quote-price">
          <span className="metric-label">Last close</span>
          <div className="price-row">
            <strong>{formatPrice.format(latest.close)}</strong>
            {change !== null && <span className={`change ${changeClass}`}>{change > 0 ? '+' : ''}{change.toFixed(2)}%</span>}
          </div>
          <span className="quote-date">{formatDate(latest.date)} · vs. prior close</span>
        </div>
        <div className="range-switch" role="group" aria-label="Chart range">
          {Object.keys(ranges).map(period => (
            <button key={period} type="button" onClick={() => setRange(period)} aria-pressed={range === period}>{period}</button>
          ))}
        </div>
      </div>

      <div className="chart-section">
        <div className="chart-legend" aria-label="Chart legend">
          <span><i className="legend-candle" />Price</span>
          <span><i className="legend-average" />10-day moving average</span>
          <span><i className="legend-volume" />Volume</span>
        </div>
        <StockChart data={chart} visibleDays={ranges[range]} />
      </div>

      <dl className="market-metrics">
        <div><dt>Day high</dt><dd>{formatPrice.format(latest.high)}</dd></div>
        <div><dt>Day low</dt><dd>{formatPrice.format(latest.low)}</dd></div>
        <div><dt>Volume</dt><dd>{formatVolume.format(latest.volume)}</dd></div>
        <div><dt>10-day average</dt><dd>{average === null ? '—' : formatPrice.format(average)}</dd></div>
      </dl>

      <footer className="market-footer">
        <span>{source}</span>
        {marketProgress && <span role="status" className="market-progress">{marketProgress}</span>}
        {marketError && <span role="alert" className="market-error">{marketError}</span>}
      </footer>
    </section>
  )
}

export default function App() {
  const [query, setQuery] = useState('')
  const [messages, setMessages] = useState([])
  const [progress, setProgress] = useState(null)
  const [market, setMarket] = useState({ chart: snapshot, source: snapshotSource })
  const [marketError, setMarketError] = useState('')
  const [range, setRange] = useState('1M')
  const busy = useRef(false)
  const conversation = useRef(null)
  const symbol = market.chart.symbol

  useEffect(() => {
    const panel = conversation.current
    if (panel && (messages.length || progress?.area === 'chat')) panel.scrollTop = panel.scrollHeight
  }, [messages, progress])

  async function submit(question, marketTicker) {
    const message = question.trim()
    if (!message || busy.current) return
    const area = marketTicker ? 'market' : 'chat'
    busy.current = true
    if (marketTicker) {
      setMarketError('')
    } else {
      setQuery('')
      setMessages(previous => [...previous, { question: message }])
    }
    setProgress({ area, label: marketTicker ? `Loading ${marketTicker}…` : 'Queued' })
    try {
      const job = await request('/api/jobs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: message, symbol: marketTicker ?? symbol }),
      })
      for (let attempt = 0; attempt < 185; attempt++) {
        const status = await request(`/api/jobs/${job.job_id}`)
        if (status.status === 'failed') throw new Error(status.error)
        if (status.status === 'completed') {
          const result = status.result
          if (result.chart?.candles?.length) {
            setMarket({ chart: result.chart, source: result.sources?.join(' · ') || 'Source unavailable' })
            setMarketError('')
          } else if (marketTicker) {
            throw new Error(result.answer || 'Price data is unavailable.')
          }
          if (!marketTicker) setMessages(previous => [...previous, { result }])
          return
        }
        if (status.status === 'running') setProgress({ area, label: `Analyzing · ${status.progress}%` })
        await new Promise(resolve => setTimeout(resolve, 1000))
      }
      throw new Error('The job is taking longer than expected. Try again.')
    } catch (error) {
      if (marketTicker) setMarketError(error.message)
      else setMessages(previous => [...previous, { error: error.message }])
    } finally {
      busy.current = false
      setProgress(null)
    }
  }

  function loadMarket(ticker) {
    submit(`Show ${ticker} price and volume`, ticker)
  }

  return (
    <div className="workspace">
      <aside className="sidebar" aria-label="Market watchlist">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true"><i /><i /><i /></span>
          <span>Financial Harness</span>
        </div>
        <div className="watchlist">
          <h2>Watchlist</h2>
          {Object.entries(companies).map(([ticker, company]) => (
            <button type="button" key={ticker} aria-pressed={symbol === ticker}
              onClick={() => loadMarket(ticker)} disabled={!!progress}>
              <span><strong>{ticker}</strong><small>{company}</small></span>
              <span aria-hidden="true" className="watch-arrow">›</span>
            </button>
          ))}
        </div>
      </aside>

      <main className="main-content">
        <header className="workspace-header">
          <h1>Market overview</h1>
          <p>Explore price action, company financials, and market scenarios.</p>
        </header>

        <div className="dashboard">
          <MarketPanel market={market} range={range} setRange={setRange} refresh={() => loadMarket(symbol)}
            marketProgress={progress?.area === 'market' ? progress.label : null}
            marketError={marketError} busy={!!progress} />

          <section className="panel assistant-panel" aria-labelledby="assistant-title">
            <header className="assistant-header">
              <span className="assistant-mark" aria-hidden="true">✦</span>
              <div><h2 id="assistant-title">Stock Assistant</h2><p>Researching {symbol}</p></div>
            </header>

            <div className="conversation" ref={conversation} aria-label="Conversation" aria-live="polite">
              {!messages.length && (
                <div className="assistant-empty">
                  <h3>What would you like to research?</h3>
                  <p>Start with a question or choose an analysis below.</p>
                  <PromptButtons symbol={symbol} busy={!!progress} submit={submit} />
                </div>
              )}
              {messages.map((message, index) => message.question ? (
                <p className="question" key={index}>{message.question}</p>
              ) : message.result ? <Result key={index} data={message.result} /> : (
                <p className="error" key={index} role="alert">{message.error}</p>
              ))}
              {progress?.area === 'chat' && <p className="chat-progress" role="status">{progress.label}</p>}
            </div>

            {!!messages.length && <PromptButtons symbol={symbol} busy={!!progress} submit={submit} compact />}
            <form className="composer" onSubmit={event => { event.preventDefault(); submit(query) }}>
              <div className="composer-row">
                <input aria-label="Your stock question" value={query} onChange={event => setQuery(event.target.value)}
                  placeholder={`Ask about ${symbol}…`} maxLength={500} />
                <button type="submit" disabled={!query.trim() || !!progress}>Send <span aria-hidden="true">↑</span></button>
              </div>
              <p>Prices are historical. Check sources and assumptions in each answer.</p>
            </form>
          </section>
        </div>
      </main>
    </div>
  )
}
