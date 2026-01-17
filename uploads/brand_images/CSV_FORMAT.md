# CSV Format for Past Posts Analysis

## Required Columns

Your CSV file must have exactly 2 columns:

1. **image** - The filename of the image (must exist in this folder)
2. **likes** - The number of likes the post received

## Example CSV Format

```csv
image,likes
post1.jpg,1500
post2.png,3200
post3.jpg,850
post4.png,4100
post5.jpg,2300
```

## Requirements

- ✅ CSV file must be in `uploads/brand_images/` folder
- ✅ Image files mentioned in CSV must also be in `uploads/brand_images/` folder
- ✅ Minimum 2 posts required for analysis
- ✅ Use exact filenames including extensions

## How to Use

1. Upload your CSV file using the **Brand Image** button (📎)
2. Upload all corresponding images using the **Brand Image** button
3. Turn ON the **"🤖 Analyze past posts by AI"** toggle
4. Click **"Run Analysis"** button
5. Wait for analysis to complete (may take a few minutes)
6. Results saved to `uploads/analyze.json`

## Example Files Structure

```
uploads/brand_images/
├── brand_data_20260117_120000.csv  ← Your CSV
├── post1.jpg                        ← Your images
├── post2.png
├── post3.jpg
└── post4.png
```

## Analysis Output

The analysis will identify:
- Visual style patterns in high-performing posts
- Color palettes that work best
- Composition techniques
- Subject matter preferences
- And more...

Results include AI-generated insights and recommendations for future content!
