import { useEffect, useRef } from 'react'
import { CandlestickSeries, createChart, HistogramSeries, LineSeries } from 'lightweight-charts'

const defaultHint = 'Hover for daily values. Scroll or pinch to zoom.'
const number = new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 })

export default function StockChart({ data, visibleDays }) {
  const container = useRef(null)
  const tooltip = useRef(null)
  const chartRef = useRef(null)

  useEffect(() => {
    const chart = createChart(container.current, {
      autoSize: true,
      layout: {
        background: { color: '#101823' }, textColor: '#91a1b7',
        fontFamily: 'Inter, system-ui, sans-serif',
        panes: { separatorColor: '#233145', separatorHoverColor: '#2c4259' },
      },
      grid: { vertLines: { color: '#1b2838' }, horzLines: { color: '#1b2838' } },
      rightPriceScale: { borderColor: '#253245', entireTextOnly: true },
      timeScale: { borderColor: '#253245' },
      crosshair: { vertLine: { color: '#61748b' }, horzLine: { color: '#61748b' } },
    })
    const prices = chart.addSeries(CandlestickSeries, {
      upColor: '#35d6ad', downColor: '#fa7589', borderVisible: false,
      wickUpColor: '#35d6ad', wickDownColor: '#fa7589',
    })
    const volume = chart.addSeries(HistogramSeries, {
      priceFormat: { type: 'volume' }, priceLineVisible: false, lastValueVisible: false,
    }, 1)
    const indicator = chart.addSeries(LineSeries, {
      color: '#f4bd6a', lineWidth: 2, priceLineVisible: false, lastValueVisible: false,
    })
    const candles = [...data.candles].sort((a, b) => a.date.localeCompare(b.date))
    prices.setData(candles.map(({ date, open, high, low, close }) => ({ time: date, open, high, low, close })))
    volume.setData(candles.map(({ date, volume, close, open }) => ({
      time: date, value: volume, color: close >= open ? '#227963' : '#8e4153',
    })))
    indicator.setData(candles.slice(9).map(({ date }, i) => ({
      time: date, value: candles.slice(i, i + 10).reduce((sum, candle) => sum + candle.close, 0) / 10,
    })))
    chart.panes()[1].setHeight(80)
    chart.subscribeCrosshairMove(({ time, seriesData }) => {
      const point = seriesData.get(prices)
      const trades = seriesData.get(volume)
      if (tooltip.current) {
        tooltip.current.textContent = point && trades
          ? `${time} · O ${number.format(point.open)} · H ${number.format(point.high)} · L ${number.format(point.low)} · C ${number.format(point.close)} · Vol ${number.format(trades.value)}`
          : defaultHint
      }
    })
    chartRef.current = chart
    return () => {
      chartRef.current = null
      chart.remove()
    }
  }, [data])

  useEffect(() => {
    const last = data.candles.length - 1
    chartRef.current?.timeScale().setVisibleLogicalRange({
      from: Math.max(-0.5, last - visibleDays + 0.5), to: last + 0.75,
    })
    if (tooltip.current) tooltip.current.textContent = defaultHint
  }, [data, visibleDays])

  return (
    <figure className="stock-chart" aria-label={`${data.symbol} candlestick, moving average and volume chart`}>
      <div ref={container} className="chart-canvas" />
      <figcaption ref={tooltip}>{defaultHint}</figcaption>
    </figure>
  )
}
