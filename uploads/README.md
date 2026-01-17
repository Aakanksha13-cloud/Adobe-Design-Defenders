# Uploads Folder

This folder stores all uploaded files and exported content from the Content Publisher add-on.

## File Types Stored Here:

1. **Brand Images** - Images uploaded via the Brand Image button
   - Format: `brand_image_YYYYMMDD_HHMMSS.*`
   - Example: `brand_image_20260117_004800.png`

2. **Brand Guidelines** - Documents uploaded via the Brand Guidelines button
   - Format: `brand_guidelines_YYYYMMDD_HHMMSS.*`
   - Example: `brand_guidelines_20260117_004800.pdf`

3. **Compliance Exports** - PNG exports from the Compliance Checker
   - Format: `compliance_check_YYYYMMDD_HHMMSS.png`
   - Example: `compliance_check_20260117_004800.png`

## API Endpoints:

- `POST /api/upload/brand-image` - Upload brand image
- `POST /api/upload/brand-guidelines` - Upload brand guidelines document
- `POST /api/upload/compliance-export` - Save exported PNG from compliance check
- `GET /api/uploads/list` - List all uploaded files

## Note:

Files in this folder are automatically timestamped to prevent overwrites.
