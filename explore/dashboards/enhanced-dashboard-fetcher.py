from google.cloud import monitoring_dashboard_v1
from google.cloud import monitoring_v3
from google.cloud.monitoring_dashboard_v1 import DashboardsServiceClient
from google.cloud.monitoring_v3 import AlertPolicy
from typing import Dict, List, Any, Optional, Union
import json
import yaml
from datetime import datetime, timedelta
import asyncio
from dataclasses import dataclass
from enum import Enum
import pytz
from concurrent.futures import ThreadPoolExecutor

class WidgetType(Enum):
    XY_CHART = "xy_chart"
    TIME_SERIES = "time_series"
    SCORECARD = "scorecard"
    TEXT = "text"
    ALERT_CHART = "alert_chart"
    GAUGE = "gauge"
    HEATMAP = "heatmap"
    TABLE = "table"
    LOGS_PANEL = "logs_panel"
    COLLAPSIBLE_GROUP = "collapsible_group"
    BLANK = "blank"
    PIE_CHART = "pie_chart"

@dataclass
class TimeSeriesQuery:
    query: str
    display_name: str
    threshold_value: Optional[float] = None
    threshold_type: Optional[str] = None
    widget_type: Optional[str] = None
    aggregation: Optional[Dict] = None
    filters: Optional[List[str]] = None
    
@dataclass
class QueryOptions:
    start_time: datetime
    end_time: datetime
    alignment_period: str = "60s"
    aggregation: Optional[Dict] = None
    filters: Optional[List[str]] = None
    page_size: int = 1000
    cross_series_reducer: Optional[str] = None
    group_by_fields: Optional[List[str]] = None

class DashboardWidgetParser:
    """Parser for different dashboard widget types"""
    
    @staticmethod
    def parse_gauge(gauge) -> Dict:
        """Parse gauge widget information"""
        gauge_info = {
            'queries': [],
            'thresholds': [],
            'gauge_view_type': gauge.gauge_view.type_.name if hasattr(gauge, 'gauge_view') else None
        }
        
        if gauge.time_series_query:
            query_info = TimeSeriesQuery(
                query=gauge.time_series_query.time_series_filter,
                display_name=gauge.gauge_view.display_name if hasattr(gauge, 'gauge_view') else "Gauge",
                widget_type=WidgetType.GAUGE.value,
                aggregation=gauge.time_series_query.aggregation if hasattr(gauge.time_series_query, 'aggregation') else None
            )
            gauge_info['queries'].append(vars(query_info))
            
        if hasattr(gauge, 'thresholds'):
            for threshold in gauge.thresholds:
                threshold_info = {
                    'value': threshold.value,
                    'color': threshold.color,
                    'label': threshold.label if hasattr(threshold, 'label') else None
                }
                gauge_info['thresholds'].append(threshold_info)
                
        return gauge_info

    @staticmethod
    def parse_heatmap(heatmap) -> Dict:
        """Parse heatmap widget information"""
        heatmap_info = {
            'queries': [],
            'bucket_options': {},
            'color_scheme': {}
        }
        
        if heatmap.time_series_query:
            query_info = TimeSeriesQuery(
                query=heatmap.time_series_query.time_series_filter,
                display_name="Heatmap",
                widget_type=WidgetType.HEATMAP.value,
                aggregation=heatmap.time_series_query.aggregation if hasattr(heatmap.time_series_query, 'aggregation') else None
            )
            heatmap_info['queries'].append(vars(query_info))
            
        if hasattr(heatmap, 'bucket_options'):
            heatmap_info['bucket_options'] = {
                'num_buckets': heatmap.bucket_options.num_buckets if hasattr(heatmap.bucket_options, 'num_buckets') else None,
                'bucket_bounds': list(heatmap.bucket_options.bucket_bounds) if hasattr(heatmap.bucket_options, 'bucket_bounds') else None
            }
            
        return heatmap_info

    @staticmethod
    def parse_table(table) -> Dict:
        """Parse table widget information"""
        table_info = {
            'queries': [],
            'column_settings': []
        }
        
        if table.time_series_query:
            query_info = TimeSeriesQuery(
                query=table.time_series_query.time_series_filter,
                display_name="Table",
                widget_type=WidgetType.TABLE.value,
                aggregation=table.time_series_query.aggregation if hasattr(table.time_series_query, 'aggregation') else None
            )
            table_info['queries'].append(vars(query_info))
            
        if hasattr(table, 'column_settings'):
            for column in table.column_settings:
                column_info = {
                    'column': column.column if hasattr(column, 'column') else None,
                    'display_name': column.display_name if hasattr(column, 'display_name') else None,
                }
                table_info['column_settings'].append(column_info)
                
        return table_info

    @staticmethod
    def parse_logs_panel(logs_panel) -> Dict:
        """Parse logs panel widget information"""
        return {
            'filter': logs_panel.filter if hasattr(logs_panel, 'filter') else None,
            'resource_names': list(logs_panel.resource_names) if hasattr(logs_panel, 'resource_names') else None
        }

class QueryExecutor:
    """Handles execution of different types of queries"""
    
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.monitoring_client = monitoring_v3.MetricServiceClient()
        
    async def execute_query(self, query: str, options: QueryOptions) -> List[Dict]:
        """Execute a time series query with options"""
        try:
            request = monitoring_v3.QueryTimeSeriesRequest(
                name=f"projects/{self.project_id}",
                query=query,
                interval=monitoring_v3.TimeInterval(
                    start_time=options.start_time,
                    end_time=options.end_time
                )
            )
            
            if options.aggregation:
                request.aggregation = options.aggregation
                
            if options.filters:
                request.filter = ' AND '.join(options.filters)
                
            response = self.monitoring_client.query_time_series(request)
            return self._process_time_series_response(response, options)
            
        except Exception as e:
            print(f"Error executing query: {e}")
            return []
            
    def _process_time_series_response(self, response, options: QueryOptions) -> List[Dict]:
        """Process time series response with advanced options"""
        time_series_data = []
        
        for time_series in response:
            points = []
            for point in time_series.points:
                point_value = self._extract_point_value(point.value)
                points.append({
                    'timestamp': point.interval.end_time.isoformat(),
                    'value': point_value,
                    'interval': {
                        'start': point.interval.start_time.isoformat(),
                        'end': point.interval.end_time.isoformat()
                    }
                })
                
            # Add metadata
            metadata = {
                'metric': {
                    'type': time_series.metric.type,
                    'labels': dict(time_series.metric.labels)
                },
                'resource': {
                    'type': time_series.resource.type,
                    'labels': dict(time_series.resource.labels)
                }
            }
            
            # Apply group by if specified
            if options.group_by_fields:
                group_key = tuple(metadata['metric']['labels'].get(field) for field in options.group_by_fields)
                metadata['group_key'] = group_key
                
            time_series_data.append({
                'metadata': metadata,
                'points': points
            })
            
        # Apply cross-series reduction if specified
        if options.cross_series_reducer:
            time_series_data = self._apply_cross_series_reduction(
                time_series_data,
                options.cross_series_reducer
            )
            
        return time_series_data
        
    def _extract_point_value(self, value) -> Union[float, int, Dict]:
        """Extract value from a time series point"""
        if value.HasField('double_value'):
            return value.double_value
        elif value.HasField('int64_value'):
            return value.int64_value
        elif value.HasField('distribution_value'):
            return {
                'count': value.distribution_value.count,
                'mean': value.distribution_value.mean,
                'sum_of_squared_deviation': value.distribution_value.sum_of_squared_deviation
            }
        return None
        
    def _apply_cross_series_reduction(self, time_series_data: List[Dict], reducer: str) -> List[Dict]:
        """Apply cross-series reduction"""
        if not time_series_data:
            return []
            
        reduced_points = []
        timestamps = sorted(set(
            point['timestamp'] 
            for series in time_series_data 
            for point in series['points']
        ))
        
        for timestamp in timestamps:
            values = [
                point['value']
                for series in time_series_data
                for point in series['points']
                if point['timestamp'] == timestamp and isinstance(point['value'], (int, float))
            ]
            
            if values:
                reduced_value = self._reduce_values(values, reducer)
                reduced_points.append({
                    'timestamp': timestamp,
                    'value': reduced_value
                })
                
        return [{
            'metadata': {'reducer': reducer},
            'points': reduced_points
        }]
        
    def _reduce_values(self, values: List[float], reducer: str) -> float:
        """Apply reduction function to values"""
        if not values:
            return None
            
        if reducer == 'REDUCE_MEAN':
            return sum(values) / len(values)
        elif reducer == 'REDUCE_MAX':
            return max(values)
        elif reducer == 'REDUCE_MIN':
            return min(values)
        elif reducer == 'REDUCE_SUM':
            return sum(values)
        return None

class EnhancedDashboardFetcher:
    """Enhanced dashboard fetcher with support for all widget types"""
    
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.dashboard_client = DashboardsServiceClient()
        self.widget_parser = DashboardWidgetParser()
        self.query_executor = QueryExecutor(project_id)
        
    def _parse_widget(self, widget) -> Dict:
        """Parse any type of widget"""
        widget_info = {
            'title': widget.title if hasattr(widget, 'title') else None,
            'widget_type': self._determine_widget_type(widget)
        }
        
        # Parse based on widget type
        if widget.xy_chart:
            widget_info.update(self._parse_xy_chart(widget.xy_chart))
        elif widget.scorecard:
            widget_info.update(self._parse_scorecard(widget.scorecard))
        elif widget.gauge:
            widget_info.update(self.widget_parser.parse_gauge(widget.gauge))
        elif widget.heatmap:
            widget_info.update(self.widget_parser.parse_heatmap(widget.heatmap))
        elif widget.table:
            widget_info.update(self.widget_parser.parse_table(widget.table))
        elif widget.logs_panel:
            widget_info.update(self.widget_parser.parse_logs_panel(widget.logs_panel))
        elif widget.collapsible_group:
            widget_info['widgets'] = [
                self._parse_widget(w) for w in widget.collapsible_group.widgets
            ]
            
        return widget_info
        
    async def execute_dashboard_queries(self, dashboard_name: str, options: QueryOptions) -> Dict:
        """Execute all queries in a dashboard with specified options"""
        dashboard = self.get_dashboard_details(dashboard_name)
        results = {}
        
        async def process_widget(widget):
            if 'queries' in widget:
                widget_results = {}
                for query in widget['queries']:
                    try:
                        result = await self.query_executor.execute_query(
                            query['query'],
                            options
                        )
                        widget_results[query['display_name']] = result
                    except Exception as e:
                        print(f"Error executing query {query['display_name']}: {e}")
                return widget['title'], widget_results
            return None
            
        # Process all widgets concurrently
        tasks = []
        for widget in dashboard['widgets']:
            task = process_widget(widget)
            tasks.append(task)
            
        # Wait for all queries to complete
        widget_results = await asyncio.gather(*tasks)
        
        # Combine results
        for result in widget_results:
            if result:
                title, data = result
                results[title] = data
                
        return results

async def main():
    project_id = "your-project-id"
    fetcher = EnhancedDashboardFetcher(project_id)
    
    # Example query options
    options = QueryOptions(
        start_time=datetime.utcnow() - timedelta(hours=1),
        end_time=datetime.utcnow(),
        alignment_period="300s",
        aggregation={
            "alignment_period": {"seconds": 300},
            "per_series_aligner": "ALIGN_MEAN",
            "cross_series_reducer": "REDUCE_MEAN",
            "group_by_fields": ["resource.label.pod_name"]
        },
        filters=["metric.type = starts_with(\"kubernetes.io/\")"],
        cross_series_reducer="REDUCE_MEAN",
        group_by_fields=["resource.label.pod_name"]
    )
    
    # List dashboards
    dashboards = fetcher.list_dashboards()
    
    for dashboard in dashboards:
        print(f"\nProcessing dashboard: {dashboard['display_name']}")
        
        # Execute queries with options
        results = await fetcher.execute_dashboard_queries(
            dashboard['name'],
            options
        )
        
        # Export results
        output_file = f"dashboard_data_{dashboard['display_name']}.json"
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"Exported results to {output_file}")

if __name__ == "__main__":
    asyncio.run(main())
