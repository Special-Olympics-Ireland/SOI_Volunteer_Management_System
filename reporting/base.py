"""
Base classes for report generation to avoid circular imports.
"""

from typing import Dict, List, Any
from django.db.models import QuerySet
from django.utils import timezone


class BaseReportGenerator:
    """
    Base class for all report generators with common functionality.
    """
    
    def __init__(self, report):
        self.report = report
        self.parameters = report.parameters or {}
        self.start_time = None
        self.metrics = None
    
    def start_generation(self):
        """Initialize report generation"""
        from .models import ReportMetrics
        
        self.start_time = timezone.now()
        self.report.status = self.report.Status.GENERATING
        self.report.started_at = self.start_time
        self.report.progress_percentage = 0
        self.report.save()
        
        # Create metrics record
        self.metrics, created = ReportMetrics.objects.get_or_create(
            report=self.report,
            defaults={
                'rows_processed': 0,
                'columns_included': 0,
                'filters_applied': list(self.parameters.keys()),
                'data_completeness_percent': 100.0,
                'error_count': 0,
                'warning_count': 0
            }
        )
    
    def update_progress(self, percentage: int, message: str = ""):
        """Update generation progress"""
        self.report.progress_percentage = min(100, max(0, percentage))
        if message:
            self.report.error_message = message
        self.report.save()
    
    def complete_generation(self, file_path: str, file_size: int, total_records: int):
        """Complete report generation"""
        end_time = timezone.now()
        self.report.status = self.report.Status.COMPLETED
        self.report.completed_at = end_time
        self.report.progress_percentage = 100
        self.report.file_path = file_path
        self.report.file_size = file_size
        self.report.total_records = total_records
        self.report.generation_time = end_time - self.start_time
        self.report.save()
        
        # Update metrics
        if self.metrics:
            self.metrics.rows_processed = total_records
            self.metrics.save()
    
    def fail_generation(self, error_message: str):
        """Mark report generation as failed"""
        self.report.status = self.report.Status.FAILED
        self.report.error_message = error_message
        self.report.progress_percentage = 0
        self.report.save()
        
        # Update metrics
        if self.metrics:
            self.metrics.error_count += 1
            self.metrics.save()
    
    def get_queryset(self) -> QuerySet:
        """Get the base queryset for the report - to be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement get_queryset()")
    
    def get_columns(self) -> List[Dict[str, Any]]:
        """Get column definitions for the report - to be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement get_columns()")
    
    def format_row_data(self, obj: Any) -> List[Any]:
        """Format a single row of data - to be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement format_row_data()") 