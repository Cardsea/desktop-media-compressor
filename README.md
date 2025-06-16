# Media Compressor Suite

A PyQt5 GUI application for compressing both videos and images with adjustable target settings.

## Features

### Video Compression
- 🎬 Compress any video file format
- 🎯 Set target file size from 1 MB to 1 GB using an intuitive dial
- ⚡ Multiple quality presets (Ultra Fast to Very Slow)
- 📊 Real-time progress tracking

### Image Compression  
- 🖼️ Batch image compression and optimization
- 🎨 Quality control with visual preview
- 📁 Support for JPEG, PNG, BMP, TIFF, GIF formats
- 🔄 Format conversion (JPEG/PNG/Keep Original)
- 📏 Optional image resizing

### General Features
- 🌙 Modern dark theme interface
- ❌ Cancel compression mid-process
- 📂 Easy file selection with drag & drop support
- 💾 Automatic output file naming

## Requirements

- Python 3.6+
- PyQt5
- Pillow (PIL)
- FFmpeg (for video compression only)

## Installation

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Install FFmpeg (for video compression):
   - **macOS**: `brew install ffmpeg`
   - **Windows**: Download from [https://ffmpeg.org/](https://ffmpeg.org/)
   - **Linux**: `sudo apt install ffmpeg`

## Usage

1. Run the application:
```bash
python media_compressor.py
```

2. Choose between Video Compressor and Image Compressor tabs
3. Select your media files
4. Adjust compression settings
5. Click "Start Compression"

## Video Compression

The video compressor allows you to:
- Select target output size (1 MB to 1 GB)
- Choose compression speed vs quality trade-off
- Preview compression settings before processing

## Image Compression

The image compressor provides:
- Batch processing of multiple images
- Quality adjustment (10% to 100%)
- Format conversion capabilities
- Live preview of selected images
- Compression statistics

## How It Works

### Video Compression
1. Analyzes input video to determine duration
2. Calculates optimal bitrate for target file size  
3. Uses H.264 video compression with AAC audio
4. Saves compressed video with "_compressed" suffix

### Image Compression
1. Loads images using PIL/Pillow
2. Applies quality settings and format conversion
3. Optimizes file size while preserving visual quality
4. Shows before/after file size comparison

## Quality Presets

### Video
- **Ultra Fast**: Fastest compression, larger file size
- **Fast/Medium**: Balanced speed and quality
- **Slow/Very Slow**: Best quality, smaller file size

### Images
- **10-50%**: Maximum compression, suitable for web thumbnails
- **60-80%**: Good balance for web images
- **85-100%**: High quality for print or archival

## Output

- Video: Compressed videos saved with "_compressed" suffix
- Images: Processed images saved with "_compressed" suffix
- All files saved in same directory as originals

## Troubleshooting

### Video Issues
- Ensure FFmpeg is installed and accessible
- Try different quality presets if compression fails
- Check that input video is not corrupted

### Image Issues  
- Verify image formats are supported
- Try reducing quality setting for very large images
- Ensure sufficient disk space for output files

## Created by Cardiff (Cardsea)

Desktop companion to the Media Compressor Suite web application! 