# Sample Chatbot Questions

This document contains likely questions stakeholders will ask to optimize engagement and content strategy.

---

## Channel Mix Optimization

Questions about which channels (Intranet, Email, Other) drive the best results.

### Channel Performance
- Which channel drives the most unique visitors?
- What is the UV breakdown by channel (Intranet vs Email vs Other)?
- Which channel has the highest engagement rate?
- How does Email traffic compare to Intranet traffic this month?
- What percentage of our traffic comes from Email?
- Which channel drives the most likes and comments?

### Channel Trends
- How has Email traffic changed over the last 3 months?
- Is Intranet traffic growing or declining?
- Which channel showed the biggest growth last quarter?
- What is the weekly trend for Email referrals?

### Channel + Content
- Which content types perform best when shared via Email?
- Do articles get more engagement from Email or Intranet traffic?
- What themes get the most views from Email referrals?

---

## Content Performance

Questions about which content resonates with employees.

### Top Content
- What are the top 10 pages by views this month?
- Which articles got the most engagement last week?
- What are the most liked pages this quarter?
- Which pages have the most comments?
- What content has the highest engagement rate?

### Content by Type
- How do articles perform compared to overview pages?
- Which content type gets the most views?
- Do videos get more engagement than articles?
- What is the average engagement rate for news articles?

### Content by Theme/Topic
- Which themes drive the most traffic?
- What topics have the highest engagement?
- How does "Who-We-Are" content perform compared to "Technology"?
- Which news categories get the most views?
- What is the best performing topic this month?

### Content by Category
- How does "Strategy" news perform compared to "Culture" news?
- Which news category has the highest engagement rate?
- What business topics drive the most unique visitors?

---

## Engagement Analysis

Questions about likes, comments, and overall engagement.

### Engagement Metrics
- What is our overall engagement rate this month?
- How many total likes did we get last week?
- What is the average number of comments per article?
- How does this month's engagement compare to last month?

### Engagement Trends
- Is engagement increasing or decreasing over time?
- What was our peak engagement day this month?
- How does weekend engagement compare to weekdays?
- What is the monthly engagement trend for the last 6 months?

### High/Low Performers
- Which pages have zero engagement?
- What content has the highest like-to-view ratio?
- Which articles got comments but no likes?

---

## Audience Analysis

Questions about who is consuming the content.

### By Region
- Which region has the most unique visitors?
- How does EMEA engagement compare to Americas?
- What content is most popular in APAC?
- Which region has the highest engagement rate?

### By Business Division
- Which business division visits the intranet most?
- How does Investment Bank traffic compare to Global Wealth Management?
- What content do Group Functions employees engage with most?
- Which division has the lowest engagement?

### By Employee Type
- What percentage of visitors are contractors vs employees?
- Do interns engage more than full-time employees?
- How does external staff consumption compare to employees?

---

## Time-Based Analysis

Questions about trends and patterns over time.

### Daily/Weekly Patterns
- Which day of the week has the highest traffic?
- What time patterns do we see in page views?
- Is Monday or Friday busier for intranet traffic?
- How does weekend traffic compare to weekdays?

### Monthly/Quarterly Trends
- What is the UV trend for the last 3 months?
- How did Q4 compare to Q3 in terms of engagement?
- Which month had the highest traffic this year?
- Is traffic growing month over month?

### Year-over-Year
- How does this January compare to last January?
- What is our year-over-year growth in unique visitors?

---

## Website/Portal Analysis

Questions about specific websites or portals.

### Website Performance
- Which website has the most traffic?
- How does the HR Portal compare to the main Intranet?
- What is the engagement rate for each website?
- Which portal is growing fastest?

### Website + Content
- What are the top pages on the Intranet this month?
- Which content type performs best on the HR Portal?
- What themes drive traffic to each website?

---

## Comparative Analysis

Questions comparing different dimensions.

### A/B Comparisons
- How does "Culture" content perform vs "Strategy" content?
- Which performs better: articles or overview pages?
- Email vs Intranet: which drives more engagement?
- EMEA vs Americas: who engages more?

### Benchmarking
- How does this page compare to similar pages?
- Is this article performing above or below average?
- How does our engagement rate compare to last quarter?

---

## Strategic Questions

Higher-level questions for content strategy.

### Content Strategy
- What type of content should we produce more of?
- Which themes should we focus on to increase engagement?
- What content gaps do we have?
- What topics are underperforming?

### Channel Strategy
- Should we increase Email distribution?
- Which content should we prioritize for Email campaigns?
- How can we improve Intranet discovery?

### Audience Strategy
- How can we increase engagement in APAC?
- Which division should we target with more content?
- What content resonates with Investment Bank employees?

---

## Specific Page/Content Questions

Questions about individual pages or articles.

### Page Lookup
- How is the page "Company News" performing?
- Show me the metrics for pages containing "Q3 Results"
- What are the stats for pages about "Employee Benefits"?

### Page Details
- Who is viewing this page? (by region/division)
- What channel drives traffic to this page?
- How has this page performed over the last month?

---

## Data Export/Reporting

Questions about getting data out.

### Reports
- Give me a summary of this month's performance
- What are the key metrics for last week?
- Can you show me the top 10 pages with their engagement metrics?

### Comparisons
- Compare this month to last month
- Show me the performance difference between Q3 and Q4
- How does this week compare to the same week last month?

---

## Notes for Chatbot Implementation

1. **Date handling:** Users will refer to dates naturally ("this month", "last week", "Q3", "October"). The chatbot needs to convert these to `visitdatekey` ranges.

2. **Engagement rate:** Calculate as `(likes + comments) / views * 100`

3. **Channel = referrerapplicationid:** Map user terms like "Email channel" to the `referrerapplicationid` column.

4. **Content type questions:** May refer to `contenttype`, `theme`, `topic`, or `newscategory` - clarify if ambiguous.

5. **Region/Division:** Default to employee's region (`employeeregion`) and division (`employeebusinessdivision`), not content target region.

6. **"Best performing":** Could mean highest UV, most views, or best engagement rate - may need clarification.
