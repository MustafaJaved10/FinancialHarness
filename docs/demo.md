# Presentation and demo

## Slide 1 · The problem

Stock research often starts with a chart, a company report and a separate calculation. Financial Harness brings those into one chat and shows the source and assumptions.

## Slide 2 · What the app does

Ask for IBM’s price and volume to see candles and a moving average. Ask for earnings and valuation to see the reporting period and financial figures. Compare two tickers or test a what-if question.

## Slide 3 · How it works

The browser sends a question to the API. Celery takes the job from Redis, fetches source data through the MCP tools, and sends calculation inputs to the network-disabled Python sandbox. Redis holds progress and the final answer.

## Slide 4 · Live walkthrough

1. Ask **Show me IBM price and volume**. Hover over a candle and point out the source and date.
2. Ask **Show IBM earnings and valuation**. Point out the reported quarter and the table.
3. Ask **What if $1,000 drops 10%?** Watch the job finish and show the $900 result and assumptions.
4. If using saved data, point out the saved-copy label.
