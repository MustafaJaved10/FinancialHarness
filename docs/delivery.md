# Team delivery

## Jira backlog

| Epic | Story | Owner | Acceptance check |
|---|---|---|---|
| Data + MCP | Fetch daily candles and volume | Yasir | The connector returns price, volume, source, and last trading date. |
| Data + MCP | Fetch quarterly company data | Yasir | IBM includes revenue, profit, EPS, reporting period, and valuation. |
| Harness + analysis | Route questions and explain results | Mustafa | Technical and financial queries return an answer with sources and assumptions. |
| Harness + analysis | Run comparisons and scenarios | Mustafa | Two stocks compare on matching dates. Projection and what-if show assumptions. |
| Harness + analysis | Present and rehearse the demo | Mustafa | Demonstrate one financial question and one background scenario. |
| UI + Miro | Show chat, charts and tables | Shahzaib | User can submit a question and interact with candle, volume and moving-average views. |
| UI + Miro | Show background progress and failures | Shahzaib | Status changes show while the job runs and the result appears when it completes. |
| UI + Miro | Publish design board | Shahzaib | Miro shows research, user journey, wireframes, and system flow. |
| Integration + deployment | Connect API, queue, and sandbox | Hannan | Smoke test verifies a saved answer after the job completes. |
| Integration + deployment | Set up repository checks and architecture | Hannan | Pull request has CI and an AWS-style diagram. |
| Integration + deployment | Deploy and verify a reviewer link | Hannan | A reviewer can open the app and submit a working question. |

## Miro board content

- **Research:** Stock questions often require a price chart and company reports from different sources. Users need to see where the answer came from and when the data was recorded.
- **Journey:** Open app → choose a question → see job status → read the answer → inspect the chart or table → ask a follow-up.
- **Wireframes:** Chat header and suggested questions. Conversation column with answer, chart, table and sources. Bottom composer with text field and Send. Loading and error states inside the conversation.
- **System flow:** Browser → API → Redis → worker. Worker fetches MCP data and sends inputs to the isolated calculation service. Browser reads the saved answer by job ID.
