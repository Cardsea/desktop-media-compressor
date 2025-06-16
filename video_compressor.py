#!/usr/bin/env python3
"""
Video Compressor - A PyQt5 GUI application for compressing video files
Author: Cardiff (Cardsea)
"""

import sys
import os
import subprocess
import threading
import json
from pathlib import Path
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                             QWidget, QPushButton, QLabel, QProgressBar, QFileDialog,
                             QMessageBox, QTextEdit, QGroupBox, QGridLayout, QDial,
                             QSlider, QSpinBox, QComboBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QPalette, QColor, QIcon

class CompressionWorker(QThread):
    progress_updated = pyqtSignal(int)
    status_updated = pyqtSignal(str)
    compression_finished = pyqtSignal(bool, str)
    
    def __init__(self, input_file, output_file, target_size_mb, quality_preset):
        super().__init__()
        self.input_file = input_file
        self.output_file = output_file
        self.target_size_mb = target_size_mb
        self.quality_preset = quality_preset
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
        
    def run(self):
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

class VideoCompressor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.input_file = ""
        self.compression_worker = None
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("Video Compressor - by Cardiff")
        self.setGeometry(100, 100, 800, 600)
        
        # Set dark theme
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2b2b2b;
                color: #ffffff;
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
        """)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        layout = QVBoxLayout(central_widget)
        
        # Title
        title_label = QLabel("🎬 Video Compressor")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setFont(QFont("Arial", 20, QFont.Bold))
        layout.addWidget(title_label)
        
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
        
        # Info text
        info_text = QTextEdit()
        info_text.setMaximumHeight(100)
        info_text.setPlainText(
            "Instructions:\n"
            "1. Select a video file using the button above\n"
            "2. Adjust the target file size using the dial (1 MB to 1 GB)\n"
            "3. Choose quality preset (slower = better quality)\n"
            "4. Click 'Start Compression' to begin\n\n"
            "Note: FFmpeg must be installed on your system!"
        )
        info_text.setReadOnly(True)
        layout.addWidget(info_text)
        
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
            self.input_file, str(output_path), target_size_mb, quality_preset
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

def main():
    app = QApplication(sys.argv)
    
    # Check if ffmpeg is available
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Critical)
        msg_box.setWindowTitle("FFmpeg Not Found")
        msg_box.setText("FFmpeg is required but not found on your system.")
        msg_box.setInformativeText(
            "Please install FFmpeg:\n\n"
            "macOS: brew install ffmpeg\n"
            "Windows: Download from https://ffmpeg.org/\n"
            "Linux: sudo apt install ffmpeg"
        )
        msg_box.exec_()
        return
    
    window = VideoCompressor()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main() 