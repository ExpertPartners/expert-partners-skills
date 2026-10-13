# Data Collection

Meta changes these screens often. Labels and paths below are what to look for, not guarantees. If a label differs, look for the equivalent. If you can't find a metric after a reasonable look, mark it missing, and don't guess.

## Metrics to collect for every post

| Field | What it is | Notes |
|---|---|---|
| Date and time posted | Publish time | Note the timezone shown. |
| Format | Reel, carousel, or image | |
| Permalink | The post URL | Needed to open posts later. |
| Caption | Full caption text | Its first line is the written hook. |
| Views | Times the post was displayed or played | Instagram now reports Views across all formats. |
| Reach | Unique accounts that saw it | Sometimes labeled "Accounts reached." |
| Likes | | |
| Comments | | |
| Shares | Shares, including sends by DM | Some screens split out "Reposts." Record both if shown. |
| Saves | | |
| Follows | Follows that came from this post | Often only in per-post insights. |
| Profile visits | Profile activity from this post | Sometimes labeled "Profile activity." |
| Link taps | External link taps | Only when shown. |
| Non-follower % | Share of views or reach from non-followers | Shown in per-post insights as followers vs. non-followers. |
| Avg watch time | Reels only | |
| Skip rate | Reels only, when shown | Share of viewers who swiped away in the first 3 seconds. |
| Reel length | Reels only | |
| Boosted? | Whether the post was promoted with paid ads | Paid reach gets excluded from comparisons. |
| Collab? | Whether it was a Collab post | Collab reach includes the partner's audience. |

Also record the account's **current follower count** and, if visible, the count at the start of the period.

## Route A: browser

### A0. Preflight

1. Open instagram.com and confirm the user is signed in to the right account. Read the handle back to them in one line.
2. Check the account type. Professional accounts show a "Professional dashboard" or "Insights" option, or "View insights" under their own posts. If none of these exist, it's a personal account, so follow the personal-account note in SKILL.md.

### A1. Meta Business Suite content table (preferred)

This is the fastest and most complete source, because it shows every post in one table.

1. Go to business.facebook.com and open **Insights**, then **Content** (the path may read "Insights > Content" or "Content > Insights").
2. If more than one account appears, choose the Instagram account the user confirmed.
3. Set the date range to the last 90 days.
4. Filter to Instagram posts (Reels, carousels, and image posts). Exclude Stories. If the table can't be filtered, read it anyway and skip every row marked Story.
5. Use the column or metric selector to show as many of these as are offered: Views, Reach, Likes, Comments, Shares, Saves, Follows, Profile visits, Link clicks. Changing which columns are displayed is a view setting and is fine. Don't change any account or business settings.
6. Read the table with page-text or accessibility-tree tools, scrolling or paging until every post in the range is captured. Check that your row count matches the number of posts shown.
7. **If the table is too long, cut off, or hard to read:** ask the user for permission to use the Export button ("Export content data from Meta Business Suite as a CSV, about 50 KB, OK?"). Browser tools usually can't open downloaded files, so ask the user to upload the downloaded file into the chat.

If Business Suite doesn't show the Instagram account (it isn't connected, or access is denied), don't try to connect it. Go to A2.

### A2. Per-post insights on instagram.com (fallback)

1. Go to the user's profile grid on instagram.com. Stay on the grid and the Reels tab. Don't open Story highlights at the top of the profile.
2. Open each post in the date range, newest first. Click "View insights" (or "Insights") and record the metrics.
3. This takes about a minute per post. If there are more than 40 posts in the range, tell the user how long it will take and offer two options: do all of them, or do the 40 most recent and switch the rest to the CSV route.

### A3. Qualitative pass (top 10 and bottom 10)

Once you have metrics and goal scores (see analysis-method.md), open each of the top 10 and bottom 10 posts by permalink and record:

- **Written hook:** the first line of the caption, exactly as written.
- **Visual hook:** for Reels and carousels, take a screenshot of the cover or first frame and write down any on-screen text. For carousels, also read slide 1 and the last slide.
- **Spoken hook:** you usually can't hear audio. If the Reel shows captions or subtitles on screen, read those. Otherwise leave it blank, and in Route B ask the user to paste it.
- **CTA:** the ask in the caption or on the final slide, word for word.
- **Audio:** original audio vs. a trending or licensed track, if shown.
- **Comments:** read the first 20-30. Record questions people asked, buying signals ("how do I join," "price?", "link?", "DM'd you"), and recurring themes. Leave out commenters' names and handles, and never copy them into the report.
- **Per-post insights you haven't recorded yet:** follows, non-follower %, watch time, skip rate.

## Route B: CSV export

Give the user these steps, adapted to what they see:

> 1. On a computer, go to **business.facebook.com** and sign in.
> 2. Open **Insights**, then **Content**.
> 3. Pick your Instagram account and set the dates to the **last 90 days**.
> 4. Filter to posts and Reels (not Stories).
> 5. Click **Export data** (or the download icon) and choose **CSV**.
> 6. Upload the file here.

If they can't access Business Suite, the fallback is to paste numbers from the Instagram app. In **Professional dashboard**, then **Content you shared**, they can open each post's insights and copy the numbers. This is slow, so offer it for the 20 most recent posts only.

Once the CSV arrives:
- **First, delete every row whose post type is Story.** Keep Reels, carousels, and image posts only. Tell the user how many Story rows you removed, in one line.
- Map the columns to the fields above. Column names vary, so match by meaning.
- The caption usually comes in a "Description" or "Caption" column, which gives you the written hook.
- For the top 10 and bottom 10 posts, list them (date plus first line) and ask the user, optionally, to paste each Reel's spoken opener and on-screen text, and the questions they've noticed in the comments. If they skip this, analyze the written hooks only and note the limitation.

## Data quality checks before analysis

- No Stories, Highlights, or Live videos are in the data. Only Reels, carousels, and image posts.
- Every post in the range is captured once (no duplicates, no gaps).
- Dates fall inside the range.
- Boosted posts are flagged.
- Missing metrics are marked as missing, not zero.
- Numbers shown rounded ("1.2K") are noted.
