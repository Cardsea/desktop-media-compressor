#!/usr/bin/env python3
"""
Media Compressor Suite - A PyQt5 GUI application for compressing videos and images
Author: Cardiff (Cardsea)
"""

import sys
import os
import subprocess
import threading
import json
from pathlib import Path
from PIL import Image, ImageTk
import io

from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                             QWidget, QPushButton, QLabel, QProgressBar, QFileDialog,
                             QMessageBox, QTextEdit, QGroupBox, QGridLayout, QDial,
                             QSlider, QSpinBox, QComboBox, QTabWidget, QCheckBox,
                             QListWidget, QListWidgetItem, QSplitter)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QPalette, QColor, QIcon, QPixmap

class CompressionWorker(QThread):
    progress_updated = pyqtSignal(int)
    status_updated = pyqtSignal(str)
    compression_finished = pyqtSignal(bool, str)
    
    def __init__(self, input_file, output_file, target_size_mb, quality_preset, compression_type='video'):
        super().__init__()
        self.input_file = input_file
        self.output_file = output_file
        self.target_size_mb = target_size_mb
        self.quality_preset = quality_preset
        self.compression_type = compression_type
        self.is_cancelled = False
        
    def cancel(self):
        self.is_cancelled = True
        
    def get_video_duration(self, file_path):
        """Get video duration in seconds using ffprobe"""
        try:
            cmd = [
                'ffprobe', '-v', 'quiet', '-print_format', 'json',
                '-show_format', file_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            data = json.loads(result.stdout)
            return float(data['format']['duration'])
        except Exception as e:
            self.status_updated.emit(f"Error getting video duration: {str(e)}")
            return None
            
    def calculate_bitrate(self, duration_seconds, target_size_mb):
        """Calculate target bitrate based on file size and duration"""
        # Convert MB to bits and account for audio (assume ~128kbps)
        target_bits = target_size_mb * 8 * 1024 * 1024
        audio_bits = 128 * 1000 * duration_seconds  # 128kbps audio
        video_bits = target_bits - audio_bits
        
        # Calculate video bitrate in kbps
        video_bitrate = max(100, int(video_bits / duration_seconds / 1000))
        return video_bitrate
        
    def compress_video(self):
        """Compress video using FFmpeg"""
        try:
            self.status_updated.emit("Analyzing video...")
            
            # Get video duration
            duration = self.get_video_duration(self.input_file)
            if duration is None:
                self.compression_finished.emit(False, "Failed to analyze video")
                return
                
            # Calculate target bitrate
            target_bitrate = self.calculate_bitrate(duration, self.target_size_mb)
            
            self.status_updated.emit(f"Compressing video (target bitrate: {target_bitrate}kbps)...")
            
            # Quality presets
            preset_map = {
                "Ultra Fast": "ultrafast",
                "Super Fast": "superfast", 
                "Very Fast": "veryfast",
                "Faster": "faster",
                "Fast": "fast",
                "Medium": "medium",
                "Slow": "slow",
                "Slower": "slower",
                "Very Slow": "veryslow"
            }
            
            # Build ffmpeg command
            cmd = [
                'ffmpeg', '-i', self.input_file,
                '-c:v', 'libx264',
                '-preset', preset_map.get(self.quality_preset, 'medium'),
                '-b:v', f'{target_bitrate}k',
                '-c:a', 'aac',
                '-b:a', '128k',
                '-y',  # Overwrite output file
                self.output_file
            ]
            
            # Run ffmpeg with progress tracking
            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            # Monitor progress (simplified - ffmpeg doesn't easily provide progress)
            progress = 0
            while process.poll() is None:
                if self.is_cancelled:
                    process.terminate()
                    self.compression_finished.emit(False, "Compression cancelled")
                    return
                    
                progress = min(progress + 2, 95)
                self.progress_updated.emit(progress)
                self.msleep(500)
                
            # Check if compression was successful
            if process.returncode == 0:
                self.progress_updated.emit(100)
                self.status_updated.emit("Compression completed successfully!")
                self.compression_finished.emit(True, f"Video compressed successfully!\nSaved to: {self.output_file}")
            else:
                stderr = process.stderr.read() if process.stderr else "Unknown error"
                self.compression_finished.emit(False, f"Compression failed: {stderr}")
                
        except Exception as e:
            self.compression_finished.emit(False, f"Error during compression: {str(e)}")
    
    def compress_image(self):
        """Compress image using PIL"""
        try:
            self.status_updated.emit("Loading image...")
            self.progress_updated.emit(10)
            
            # Open image
            with Image.open(self.input_file) as img:
                self.status_updated.emit("Processing image...")
                self.progress_updated.emit(30)
                
                # Convert RGBA to RGB if necessary
                if img.mode in ('RGBA', 'LA', 'P'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                self.progress_updated.emit(50)
                
                # Determine output format and quality
                output_path = Path(self.output_file)
                if output_path.suffix.lower() in ['.jpg', '.jpeg']:
                    format_type = 'JPEG'
                    # Quality mapping: target_size_mb is actually quality percentage for images
                    quality = min(100, max(10, int(self.target_size_mb)))
                else:
                    format_type = 'PNG'
                    quality = 95  # PNG doesn't use quality in the same way
                
                self.status_updated.emit(f"Saving compressed image (quality: {quality}%)...")
                self.progress_updated.emit(80)
                
                # Save compressed image
                save_kwargs = {'format': format_type, 'optimize': True}
                if format_type == 'JPEG':
                    save_kwargs['quality'] = quality
                
                img.save(self.output_file, **save_kwargs)
                
                self.progress_updated.emit(100)
                self.status_updated.emit("Image compression completed!")
                
                # Get file sizes for comparison
                original_size = os.path.getsize(self.input_file)
                compressed_size = os.path.getsize(self.output_file)
                reduction = ((original_size - compressed_size) / original_size) * 100
                
                self.compression_finished.emit(True, 
                    f"Image compressed successfully!\n"
                    f"Original: {self.format_size(original_size)}\n"
                    f"Compressed: {self.format_size(compressed_size)}\n"
                    f"Reduction: {reduction:.1f}%\n"
                    f"Saved to: {self.output_file}")
                
        except Exception as e:
            self.compression_finished.emit(False, f"Error during image compression: {str(e)}")
    
    def format_size(self, bytes_size):
        """Format file size in human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_size < 1024.0:
                return f"{bytes_size:.1f} {unit}"
            bytes_size /= 1024.0
        return f"{bytes_size:.1f} TB"
        
    def run(self):
        if self.compression_type == 'video':
            self.compress_video()
        else:
            self.compress_image()

class VideoCompressorTab(QWidget):
    def __init__(self):
        super().__init__()
        self.input_file = ""
        self.compression_worker = None
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # File selection group
        file_group = QGroupBox("File Selection")
        file_layout = QVBoxLayout(file_group)
        
        self.file_label = QLabel("No file selected")
        self.file_label.setWordWrap(True)
        file_layout.addWidget(self.file_label)
        
        select_button = QPushButton("📁 Select Video File")
        select_button.clicked.connect(self.select_file)
        file_layout.addWidget(select_button)
        
        layout.addWidget(file_group)
        
        # Compression settings group
        settings_group = QGroupBox("Compression Settings")
        settings_layout = QGridLayout(settings_group)
        
        # Target size dial and controls
        size_label = QLabel("Target File Size:")
        settings_layout.addWidget(size_label, 0, 0)
        
        # Create horizontal layout for size controls
        size_controls_layout = QHBoxLayout()
        
        # Size dial (1 MB to 1000 MB = 1 GB)
        self.size_dial = QDial()
        self.size_dial.setMinimum(1)
        self.size_dial.setMaximum(1000)
        self.size_dial.setValue(100)  # Default 100 MB
        self.size_dial.setNotchesVisible(True)
        self.size_dial.valueChanged.connect(self.update_size_display)
        size_controls_layout.addWidget(self.size_dial)
        
        # Size display and spinbox
        size_display_layout = QVBoxLayout()
        self.size_display_label = QLabel("100 MB")
        self.size_display_label.setAlignment(Qt.AlignCenter)
        self.size_display_label.setFont(QFont("Arial", 14, QFont.Bold))
        size_display_layout.addWidget(self.size_display_label)
        
        self.size_spinbox = QSpinBox()
        self.size_spinbox.setMinimum(1)
        self.size_spinbox.setMaximum(1000)
        self.size_spinbox.setValue(100)
        self.size_spinbox.setSuffix(" MB")
        self.size_spinbox.valueChanged.connect(self.sync_dial_from_spinbox)
        size_display_layout.addWidget(self.size_spinbox)
        
        size_controls_layout.addLayout(size_display_layout)
        settings_layout.addLayout(size_controls_layout, 0, 1)
        
        # Quality preset
        quality_label = QLabel("Quality Preset:")
        settings_layout.addWidget(quality_label, 1, 0)
        
        self.quality_combo = QComboBox()
        self.quality_combo.addItems([
            "Ultra Fast", "Super Fast", "Very Fast", "Faster", 
            "Fast", "Medium", "Slow", "Slower", "Very Slow"
        ])
        self.quality_combo.setCurrentText("Medium")
        settings_layout.addWidget(self.quality_combo, 1, 1)
        
        layout.addWidget(settings_group)
        
        # Progress group
        progress_group = QGroupBox("Compression Progress")
        progress_layout = QVBoxLayout(progress_group)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        progress_layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("Ready to compress")
        progress_layout.addWidget(self.status_label)
        
        layout.addWidget(progress_group)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        self.compress_button = QPushButton("🚀 Start Compression")
        self.compress_button.clicked.connect(self.start_compression)
        self.compress_button.setEnabled(False)
        button_layout.addWidget(self.compress_button)
        
        self.cancel_button = QPushButton("❌ Cancel")
        self.cancel_button.clicked.connect(self.cancel_compression)
        self.cancel_button.setEnabled(False)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
        
    def update_size_display(self, value):
        """Update size display when dial changes"""
        if value >= 1000:
            display_text = "1.00 GB"
        else:
            display_text = f"{value} MB"
        self.size_display_label.setText(display_text)
        self.size_spinbox.blockSignals(True)
        self.size_spinbox.setValue(value)
        self.size_spinbox.blockSignals(False)
        
    def sync_dial_from_spinbox(self, value):
        """Sync dial when spinbox changes"""
        self.size_dial.setValue(value)
        
    def select_file(self):
        """Open file dialog to select video file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Video File",
            "",
            "Video Files (*.mp4 *.avi *.mov *.mkv *.wmv *.flv *.webm *.m4v);;All Files (*)"
        )
        
        if file_path:
            self.input_file = file_path
            self.file_label.setText(f"Selected: {os.path.basename(file_path)}")
            self.compress_button.setEnabled(True)
            
    def start_compression(self):
        """Start video compression in a separate thread"""
        if not self.input_file:
            QMessageBox.warning(self, "No File", "Please select a video file first!")
            return
            
        # Get output file path
        input_path = Path(self.input_file)
        output_path = input_path.parent / f"{input_path.stem}_compressed{input_path.suffix}"
        
        # Get compression settings
        target_size_mb = self.size_dial.value()
        quality_preset = self.quality_combo.currentText()
        
        # Update UI
        self.compress_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # Start compression worker
        self.compression_worker = CompressionWorker(
            self.input_file, str(output_path), target_size_mb, quality_preset, 'video'
        )
        self.compression_worker.progress_updated.connect(self.update_progress)
        self.compression_worker.status_updated.connect(self.update_status)
        self.compression_worker.compression_finished.connect(self.compression_finished)
        self.compression_worker.start()
        
    def cancel_compression(self):
        """Cancel ongoing compression"""
        if self.compression_worker:
            self.compression_worker.cancel()
            
    def update_progress(self, value):
        """Update progress bar"""
        self.progress_bar.setValue(value)
        
    def update_status(self, message):
        """Update status label"""
        self.status_label.setText(message)
        
    def compression_finished(self, success, message):
        """Handle compression completion"""
        self.progress_bar.setVisible(False)
        self.compress_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        
        if success:
            QMessageBox.information(self, "Success", message)
            self.status_label.setText("Compression completed successfully!")
        else:
            QMessageBox.critical(self, "Error", message)
            self.status_label.setText("Compression failed!")
            
        self.compression_worker = None

class ImageCompressorTab(QWidget):
    def __init__(self):
        super().__init__()
        self.input_files = []
        self.compression_worker = None
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Create splitter for file list and preview
        splitter = QSplitter(Qt.Horizontal)
        
        # Left side - file selection and settings
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        # File selection group
        file_group = QGroupBox("File Selection")
        file_layout = QVBoxLayout(file_group)
        
        select_button = QPushButton("📁 Select Image Files")
        select_button.clicked.connect(self.select_files)
        file_layout.addWidget(select_button)
        
        self.file_list = QListWidget()
        self.file_list.setMaximumHeight(150)
        file_layout.addWidget(self.file_list)
        
        left_layout.addWidget(file_group)
        
        # Compression settings group
        settings_group = QGroupBox("Compression Settings")
        settings_layout = QGridLayout(settings_group)
        
        # Quality dial
        quality_label = QLabel("Quality Level:")
        settings_layout.addWidget(quality_label, 0, 0)
        
        quality_controls_layout = QHBoxLayout()
        
        self.quality_dial = QDial()
        self.quality_dial.setMinimum(10)
        self.quality_dial.setMaximum(100)
        self.quality_dial.setValue(80)  # Default 80%
        self.quality_dial.setNotchesVisible(True)
        self.quality_dial.valueChanged.connect(self.update_quality_display)
        quality_controls_layout.addWidget(self.quality_dial)
        
        quality_display_layout = QVBoxLayout()
        self.quality_display_label = QLabel("80%")
        self.quality_display_label.setAlignment(Qt.AlignCenter)
        self.quality_display_label.setFont(QFont("Arial", 14, QFont.Bold))
        quality_display_layout.addWidget(self.quality_display_label)
        
        self.quality_spinbox = QSpinBox()
        self.quality_spinbox.setMinimum(10)
        self.quality_spinbox.setMaximum(100)
        self.quality_spinbox.setValue(80)
        self.quality_spinbox.setSuffix("%")
        self.quality_spinbox.valueChanged.connect(self.sync_quality_dial_from_spinbox)
        quality_display_layout.addWidget(self.quality_spinbox)
        
        quality_controls_layout.addLayout(quality_display_layout)
        settings_layout.addLayout(quality_controls_layout, 0, 1)
        
        # Output format
        format_label = QLabel("Output Format:")
        settings_layout.addWidget(format_label, 1, 0)
        
        self.format_combo = QComboBox()
        self.format_combo.addItems(["JPEG (Smaller)", "PNG (Lossless)", "Keep Original"])
        settings_layout.addWidget(self.format_combo, 1, 1)
        
        # Resize option
        self.resize_checkbox = QCheckBox("Resize images")
        settings_layout.addWidget(self.resize_checkbox, 2, 0)
        
        resize_layout = QHBoxLayout()
        self.max_width_spinbox = QSpinBox()
        self.max_width_spinbox.setMinimum(100)
        self.max_width_spinbox.setMaximum(4000)
        self.max_width_spinbox.setValue(1920)
        self.max_width_spinbox.setSuffix(" px")
        resize_layout.addWidget(QLabel("Max Width:"))
        resize_layout.addWidget(self.max_width_spinbox)
        
        self.max_height_spinbox = QSpinBox()
        self.max_height_spinbox.setMinimum(100)
        self.max_height_spinbox.setMaximum(4000)
        self.max_height_spinbox.setValue(1080)
        self.max_height_spinbox.setSuffix(" px")
        resize_layout.addWidget(QLabel("Max Height:"))
        resize_layout.addWidget(self.max_height_spinbox)
        
        settings_layout.addLayout(resize_layout, 2, 1)
        
        left_layout.addWidget(settings_group)
        
        # Progress group
        progress_group = QGroupBox("Compression Progress")
        progress_layout = QVBoxLayout(progress_group)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        progress_layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("Ready to compress")
        progress_layout.addWidget(self.status_label)
        
        left_layout.addWidget(progress_group)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        self.compress_button = QPushButton("🖼️ Start Compression")
        self.compress_button.clicked.connect(self.start_compression)
        self.compress_button.setEnabled(False)
        button_layout.addWidget(self.compress_button)
        
        self.cancel_button = QPushButton("❌ Cancel")
        self.cancel_button.clicked.connect(self.cancel_compression)
        self.cancel_button.setEnabled(False)
        button_layout.addWidget(self.cancel_button)
        
        clear_button = QPushButton("🗑️ Clear All")
        clear_button.clicked.connect(self.clear_files)
        button_layout.addWidget(clear_button)
        
        left_layout.addLayout(button_layout)
        
        splitter.addWidget(left_widget)
        
        # Right side - preview
        self.preview_label = QLabel("Select images to see preview")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumSize(300, 400)
        self.preview_label.setStyleSheet("border: 1px solid #555555; border-radius: 8px;")
        splitter.addWidget(self.preview_label)
        
        splitter.setSizes([500, 300])
        
        layout.addWidget(splitter)
        
    def update_quality_display(self, value):
        """Update quality display when dial changes"""
        self.quality_display_label.setText(f"{value}%")
        self.quality_spinbox.blockSignals(True)
        self.quality_spinbox.setValue(value)
        self.quality_spinbox.blockSignals(False)
        
    def sync_quality_dial_from_spinbox(self, value):
        """Sync dial when spinbox changes"""
        self.quality_dial.setValue(value)
        
    def select_files(self):
        """Open file dialog to select image files"""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Image Files",
            "",
            "Image Files (*.jpg *.jpeg *.png *.bmp *.tiff *.gif);;All Files (*)"
        )
        
        if file_paths:
            self.input_files = file_paths
            self.update_file_list()
            self.compress_button.setEnabled(True)
            self.update_preview()
            
    def update_file_list(self):
        """Update the file list widget"""
        self.file_list.clear()
        for file_path in self.input_files:
            item = QListWidgetItem(os.path.basename(file_path))
            item.setToolTip(file_path)
            self.file_list.addItem(item)
            
    def update_preview(self):
        """Update preview with first selected image"""
        if self.input_files:
            try:
                first_image = self.input_files[0]
                pixmap = QPixmap(first_image)
                if not pixmap.isNull():
                    # Scale pixmap to fit preview while maintaining aspect ratio
                    scaled_pixmap = pixmap.scaled(280, 380, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    self.preview_label.setPixmap(scaled_pixmap)
                    
                    # Show image info
                    file_size = os.path.getsize(first_image)
                    size_text = self.format_size(file_size)
                    self.preview_label.setText("")
                    self.preview_label.setToolTip(f"{os.path.basename(first_image)}\nSize: {size_text}")
                else:
                    self.preview_label.setText("Cannot preview this image")
            except Exception as e:
                self.preview_label.setText(f"Preview error: {str(e)}")
        else:
            self.preview_label.clear()
            self.preview_label.setText("Select images to see preview")
            
    def format_size(self, bytes_size):
        """Format file size in human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_size < 1024.0:
                return f"{bytes_size:.1f} {unit}"
            bytes_size /= 1024.0
        return f"{bytes_size:.1f} TB"
            
    def clear_files(self):
        """Clear all selected files"""
        self.input_files = []
        self.file_list.clear()
        self.preview_label.clear()
        self.preview_label.setText("Select images to see preview")
        self.compress_button.setEnabled(False)
        
    def start_compression(self):
        """Start image compression for all selected files"""
        if not self.input_files:
            QMessageBox.warning(self, "No Files", "Please select image files first!")
            return
            
        # Update UI
        self.compress_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # Process first file (for demo - in real app would process all)
        first_file = self.input_files[0]
        input_path = Path(first_file)
        
        # Determine output format
        format_choice = self.format_combo.currentText()
        if "JPEG" in format_choice:
            output_path = input_path.parent / f"{input_path.stem}_compressed.jpg"
        elif "PNG" in format_choice:
            output_path = input_path.parent / f"{input_path.stem}_compressed.png"
        else:
            output_path = input_path.parent / f"{input_path.stem}_compressed{input_path.suffix}"
        
        # Get compression settings (quality for images)
        quality = self.quality_dial.value()
        
        # Start compression worker
        self.compression_worker = CompressionWorker(
            first_file, str(output_path), quality, "", 'image'
        )
        self.compression_worker.progress_updated.connect(self.update_progress)
        self.compression_worker.status_updated.connect(self.update_status)
        self.compression_worker.compression_finished.connect(self.compression_finished)
        self.compression_worker.start()
        
    def cancel_compression(self):
        """Cancel ongoing compression"""
        if self.compression_worker:
            self.compression_worker.cancel()
            
    def update_progress(self, value):
        """Update progress bar"""
        self.progress_bar.setValue(value)
        
    def update_status(self, message):
        """Update status label"""
        self.status_label.setText(message)
        
    def compression_finished(self, success, message):
        """Handle compression completion"""
        self.progress_bar.setVisible(False)
        self.compress_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        
        if success:
            QMessageBox.information(self, "Success", message)
            self.status_label.setText("Compression completed successfully!")
        else:
            QMessageBox.critical(self, "Error", message)
            self.status_label.setText("Compression failed!")
            
        self.compression_worker = None

class MediaCompressor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("Media Compressor Suite - by Cardiff")
        self.setGeometry(100, 100, 1000, 700)
        
        # Set dark theme
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QTabWidget::pane {
                border: 1px solid #555555;
                background-color: #2b2b2b;
            }
            QTabWidget::tab-bar {
                alignment: center;
            }
            QTabBar::tab {
                background-color: #404040;
                color: #ffffff;
                padding: 12px 24px;
                margin-right: 2px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
            }
            QTabBar::tab:selected {
                background-color: #4CAF50;
            }
            QTabBar::tab:hover {
                background-color: #555555;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #555555;
                border-radius: 5px;
                margin-top: 1ex;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QPushButton {
                background-color: #4CAF50;
                border: none;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
            QPushButton:disabled {
                background-color: #666666;
                color: #999999;
            }
            QLabel {
                color: #ffffff;
            }
            QProgressBar {
                border: 2px solid #555555;
                border-radius: 5px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 3px;
            }
            QListWidget {
                background-color: #404040;
                border: 1px solid #555555;
                border-radius: 4px;
                color: #ffffff;
            }
            QListWidget::item {
                padding: 4px;
                border-bottom: 1px solid #555555;
            }
            QListWidget::item:selected {
                background-color: #4CAF50;
            }
        """)
        
        # Central widget with tabs
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        
        # Title
        title_label = QLabel("🎬 Media Compressor Suite")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setFont(QFont("Arial", 20, QFont.Bold))
        layout.addWidget(title_label)
        
        subtitle_label = QLabel("Professional video and image compression tools - by Cardiff (Cardsea)")
        subtitle_label.setAlignment(Qt.AlignCenter)
        subtitle_label.setStyleSheet("color: #cccccc; margin-bottom: 20px;")
        layout.addWidget(subtitle_label)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        
        # Add video compressor tab
        self.video_tab = VideoCompressorTab()
        self.tab_widget.addTab(self.video_tab, "🎬 Video Compressor")
        
        # Add image compressor tab
        self.image_tab = ImageCompressorTab()
        self.tab_widget.addTab(self.image_tab, "🖼️ Image Compressor")
        
        layout.addWidget(self.tab_widget)
        
        # Info text
        info_text = QTextEdit()
        info_text.setMaximumHeight(80)
        info_text.setPlainText(
            "Media Compressor Suite: Choose the Video tab for video compression with size targeting (1MB-1GB), "
            "or the Image tab for batch image optimization with quality control. "
            "FFmpeg required for video compression."
        )
        info_text.setReadOnly(True)
        layout.addWidget(info_text)

def main():
    app = QApplication(sys.argv)
    
    # Check if ffmpeg is available for video compression
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle("FFmpeg Not Found")
        msg_box.setText("FFmpeg is not found on your system.")
        msg_box.setInformativeText(
            "Video compression requires FFmpeg. Image compression will still work.\n\n"
            "To install FFmpeg:\n"
            "macOS: brew install ffmpeg\n"
            "Windows: Download from https://ffmpeg.org/\n"
            "Linux: sudo apt install ffmpeg"
        )
        msg_box.exec_()
    
    window = MediaCompressor()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main() 