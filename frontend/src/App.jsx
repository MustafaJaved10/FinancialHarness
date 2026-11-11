import { useEffect, useRef, useState } from 'react'
import StockChart from './StockChart'
import './App.css'

const examples = [
  'Show me IBM price and volume',
  'Show IBM earnings and valuation',
  'Compare IBM and MSFT',
  'Project IBM over 3 years',
  'What if $1,000 drops 10%?',
]

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
    <div className="result">
      <p>{data.answer}</p>
      {data.chart && <StockChart data={data.chart} />}
      {data.table && (
        <div className="table-scroll">
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
    </div>
  )
}

export default function App() {
  const [query, setQuery] = useState('')
  const [messages, setMessages] = useState([])
  const [progress, setProgress] = useState(null)
  const [symbol, setSymbol] = useState('IBM')
  const end = useRef(null)

  useEffect(() => { end.current?.scrollIntoView({ block: 'nearest' }) }, [messages, progress])

  async function send(question) {
    if (!question.trim() || progress !== null) return
    setQuery('')
    setMessages(previous => [...previous, { question }])
    setProgress('Queued')
    try {
      const job = await request('/api/jobs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question, symbol }),
      })
      for (let attempt = 0; attempt < 185; attempt++) {
        const status = await request(`/api/jobs/${job.job_id}`)
        if (status.status === 'failed') throw new Error(status.error)
        if (status.status === 'completed') {
          const ticker = status.result.chart?.symbol
          if (ticker) setSymbol(ticker)
          setMessages(previous => [...previous, { result: status.result }])
          return
        }
        setProgress(status.status === 'running' ? `Running · ${status.progress}%` : 'Queued')
        await new Promise(resolve => setTimeout(resolve, 1000))
      }
      throw new Error('The job is taking longer than expected. Try again.')
    } catch (error) {
      setMessages(previous => [...previous, { error: error.message }])
    } finally {
      setProgress(null)
    }
  }

  return (
    <main className="assistant">
      <header className="assistant-header"><h1>AI Stock Assistant</h1><span>IBM Demo</span></header>
      <section className="conversation" aria-label="Conversation" aria-live="polite">
        <p>Ask about stock prices, company financials, or a what-if scenario.</p>
        <div className="examples">
          {examples.map(example => <button type="button" key={example} disabled={progress !== null} onClick={() => send(example)}>{example}</button>)}
        </div>
        {messages.map((message, index) => message.question ? (
          <p className="question" key={index}>{message.question}</p>
        ) : message.result ? <Result key={index} data={message.result} /> : (
          <p className="error" key={index}>{message.error}</p>
        ))}
        {progress && <p role="status">{progress}</p>}
        <div ref={end} />
      </section>
      <form className="composer" onSubmit={event => { event.preventDefault(); send(query) }}>
        <input aria-label="Your stock question" value={query} onChange={event => setQuery(event.target.value)}
          placeholder="Ask a stock question" maxLength={500} />
        <button type="submit" disabled={!query.trim() || progress !== null}>Send</button>
      </form>
    </main>
  )
}
