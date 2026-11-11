import { useEffect, useRef } from 'react'
import { CandlestickSeries, createChart, HistogramSeries, LineSeries } from 'lightweight-charts'

export default function StockChart({ data }) {
  const container = useRef(null)
  const tooltip = useRef(null)

  useEffect(() => {
    const chart = createChart(container.current, {
      autoSize: true,
      height: 320,
      layout: { background: { color: '#fff' }, textColor: '#334155' },
    })
    const prices = chart.addSeries(CandlestickSeries, {
      upColor: '#16734b', downColor: '#b42334', borderVisible: false,
      wickUpColor: '#16734b', wickDownColor: '#b42334',
    })
    const volume = chart.addSeries(HistogramSeries, { priceFormat: { type: 'volume' } }, 1)
    const indicator = chart.addSeries(LineSeries, { color: '#235ac2', lineWidth: 2, title: '10-day MA' })
    const candles = [...data.candles].sort((a, b) => a.date.localeCompare(b.date))
    prices.setData(candles.map(({ date, open, high, low, close }) => ({ time: date, open, high, low, close })))
    volume.setData(candles.map(({ date, volume, close, open }) => ({
      time: date, value: volume, color: close >= open ? '#16734b' : '#b42334',
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
          ? `${time} · Open ${point.open} · High ${point.high} · Low ${point.low} · Close ${point.close} · Volume ${trades.value.toLocaleString()}`
          : 'Hover for daily values. Scroll to zoom.'
      }
    })
    chart.timeScale().fitContent()
    return () => chart.remove()
  }, [data])

  return <figure className="stock-chart">
    <figcaption>{data.symbol} daily price ({data.currency}), 10-day moving average and volume</figcaption>
    <div ref={container} className="chart-canvas" />
    <small ref={tooltip}>Hover for daily values. Scroll to zoom.</small>
  </figure>
}
