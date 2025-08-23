"""
Research Data Export Utilities
==============================

Export utilities for generating research figures and tables from evaluation results.
Supports export for:
- 6.2 Runtime curves (input_sizes vs runtime_ms)
- 6.3 TLE/MLE rates (per-size failure analysis)
- 6.4 Iteration count analysis (iteration distribution)
"""

import json
import csv
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any, Optional
from ..utils.logger import get_logger

log = get_logger("DataExport")


class ResearchDataExporter:
    """Utilities for exporting research evaluation data in various formats."""
    
    def __init__(self, results_file: Path):
        """Initialize with results file path."""
        self.results_file = Path(results_file)
        self.results_data = self._load_results()
    
    def _load_results(self) -> Dict[str, Any]:
        """Load results from JSON file."""
        try:
            with open(self.results_file, 'r') as f:
                data = json.load(f)
            log.info(f"Loaded {len(data.get('results', []))} results from {self.results_file}")
            return data
        except Exception as e:
            log.error(f"Failed to load results from {self.results_file}: {e}")
            return {"results": []}
    
    def export_runtime_curves(self, output_dir: Path) -> List[Path]:
        """
        Export runtime curve data for Figure 6.2.
        
        Returns:
            List of generated file paths
        """
        log.info("Exporting runtime curve data...")
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        exported_files = []
        
        # Extract runtime data from successful runs with profile reports
        runtime_data = []
        for result in self.results_data.get('results', []):
            if result.get('status') == 'success' and result.get('profile_report'):
                profile = result['profile_report']
                if 'input_sizes' in profile and 'runtime_ms' in profile:
                    runtime_data.append({
                        'task_id': result['task_id'],
                        'seed': result['seed'],
                        'replan_id': result['replan_id'],
                        'input_sizes': profile['input_sizes'],
                        'runtime_ms': profile['runtime_ms'],
                        'peak_memory_mb': profile.get('peak_memory_mb', [])
                    })
        
        if not runtime_data:
            log.warning("No runtime data available for export")
            return exported_files
        
        # Export as CSV for plotting
        csv_file = output_dir / "runtime_curves.csv"
        with open(csv_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['task_id', 'seed', 'replan_id', 'input_size', 'runtime_ms', 'peak_memory_mb'])
            
            for entry in runtime_data:
                for i, size in enumerate(entry['input_sizes']):
                    runtime = entry['runtime_ms'][i] if i < len(entry['runtime_ms']) else None
                    memory = entry['peak_memory_mb'][i] if i < len(entry['peak_memory_mb']) else None
                    writer.writerow([
                        entry['task_id'], entry['seed'], entry['replan_id'],
                        size, runtime, memory
                    ])
        
        exported_files.append(csv_file)
        
        # Export as JSON for detailed analysis
        json_file = output_dir / "runtime_curves.json"
        with open(json_file, 'w') as f:
            json.dump({
                "metadata": {
                    "description": "Runtime curve data for Figure 6.2",
                    "total_curves": len(runtime_data),
                    "export_timestamp": pd.Timestamp.now().isoformat()
                },
                "curves": runtime_data
            }, f, indent=2)
        
        exported_files.append(json_file)
        
        log.info(f"Exported {len(runtime_data)} runtime curves to {len(exported_files)} files")
        return exported_files
    
    def export_tle_mle_rates(self, output_dir: Path) -> List[Path]:
        """
        Export TLE/MLE rate data for Figure 6.3.
        
        Returns:
            List of generated file paths
        """
        log.info("Exporting TLE/MLE rate data...")
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        exported_files = []
        
        # Extract TLE/MLE data
        tle_mle_data = []
        for result in self.results_data.get('results', []):
            tle_analysis = result.get('tle_analysis')
            mle_analysis = result.get('mle_analysis')
            constraints = result.get('constraints')
            
            if tle_analysis or mle_analysis:
                entry = {
                    'task_id': result['task_id'],
                    'seed': result['seed'],
                    'replan_id': result['replan_id'],
                    'status': result['status']
                }
                
                if constraints:
                    entry['runtime_limit'] = constraints.get('runtime_limit')
                    entry['memory_limit'] = constraints.get('memory_limit')
                
                if tle_analysis:
                    entry.update({
                        'tle_flags': tle_analysis['tle_flags'],
                        'tle_count': tle_analysis['tle_count'],
                        'tle_rate': tle_analysis['tle_rate'],
                        'total_input_sizes': tle_analysis['total_input_sizes']
                    })
                
                if mle_analysis:
                    entry.update({
                        'mle_flags': mle_analysis['mle_flags'],
                        'mle_count': mle_analysis['mle_count'],
                        'mle_rate': mle_analysis['mle_rate']
                    })
                
                tle_mle_data.append(entry)
        
        if not tle_mle_data:
            log.warning("No TLE/MLE data available for export")
            return exported_files
        
        # Export as CSV
        csv_file = output_dir / "tle_mle_rates.csv"
        with open(csv_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'task_id', 'seed', 'replan_id', 'status',
                'runtime_limit', 'memory_limit',
                'tle_count', 'tle_rate', 'mle_count', 'mle_rate', 'total_input_sizes'
            ])
            
            for entry in tle_mle_data:
                writer.writerow([
                    entry['task_id'], entry['seed'], entry['replan_id'], entry['status'],
                    entry.get('runtime_limit'), entry.get('memory_limit'),
                    entry.get('tle_count', 0), entry.get('tle_rate', 0),
                    entry.get('mle_count', 0), entry.get('mle_rate', 0),
                    entry.get('total_input_sizes', 0)
                ])
        
        exported_files.append(csv_file)
        
        # Export detailed JSON
        json_file = output_dir / "tle_mle_rates.json"
        with open(json_file, 'w') as f:
            json.dump({
                "metadata": {
                    "description": "TLE/MLE rate data for Figure 6.3",
                    "total_entries": len(tle_mle_data),
                    "export_timestamp": pd.Timestamp.now().isoformat()
                },
                "tle_mle_data": tle_mle_data
            }, f, indent=2)
        
        exported_files.append(json_file)
        
        log.info(f"Exported TLE/MLE data for {len(tle_mle_data)} runs to {len(exported_files)} files")
        return exported_files
    
    def export_iteration_analysis(self, output_dir: Path) -> List[Path]:
        """
        Export iteration count data for Figure 6.4.
        
        Returns:
            List of generated file paths
        """
        log.info("Exporting iteration count analysis...")
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        exported_files = []
        
        # Extract iteration data
        iteration_data = []
        for result in self.results_data.get('results', []):
            actual_iterations = result.get('actual_iterations', 0)
            legacy_iterations = result.get('iterations_used', 0)
            
            iteration_data.append({
                'task_id': result['task_id'],
                'seed': result['seed'],
                'replan_id': result['replan_id'],
                'status': result['status'],
                'actual_iterations': actual_iterations,
                'legacy_iterations': legacy_iterations,  # For comparison
                'duration_seconds': result.get('duration_seconds', 0),
                'agent_failures': result.get('agent_failures', 0)
            })
        
        # Export as CSV
        csv_file = output_dir / "iteration_analysis.csv"
        with open(csv_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'task_id', 'seed', 'replan_id', 'status',
                'actual_iterations', 'legacy_iterations', 
                'duration_seconds', 'agent_failures'
            ])
            
            for entry in iteration_data:
                writer.writerow([
                    entry['task_id'], entry['seed'], entry['replan_id'], entry['status'],
                    entry['actual_iterations'], entry['legacy_iterations'],
                    entry['duration_seconds'], entry['agent_failures']
                ])
        
        exported_files.append(csv_file)
        
        # Compute statistics
        successful_runs = [e for e in iteration_data if e['status'] == 'success']
        failed_runs = [e for e in iteration_data if e['status'] != 'success']
        
        stats = {
            "total_runs": len(iteration_data),
            "successful_runs": len(successful_runs),
            "failed_runs": len(failed_runs),
            "avg_iterations_success": sum(e['actual_iterations'] for e in successful_runs) / len(successful_runs) if successful_runs else 0,
            "avg_iterations_failed": sum(e['actual_iterations'] for e in failed_runs) / len(failed_runs) if failed_runs else 0,
            "max_iterations": max(e['actual_iterations'] for e in iteration_data) if iteration_data else 0,
            "min_iterations": min(e['actual_iterations'] for e in iteration_data) if iteration_data else 0
        }
        
        # Export detailed JSON with statistics
        json_file = output_dir / "iteration_analysis.json"
        with open(json_file, 'w') as f:
            json.dump({
                "metadata": {
                    "description": "Iteration count data for Figure 6.4",
                    "total_runs": len(iteration_data),
                    "export_timestamp": pd.Timestamp.now().isoformat()
                },
                "statistics": stats,
                "iteration_data": iteration_data
            }, f, indent=2)
        
        exported_files.append(json_file)
        
        log.info(f"Exported iteration analysis for {len(iteration_data)} runs to {len(exported_files)} files")
        log.info(f"Statistics: {stats}")
        return exported_files
    
    def export_all_research_data(self, output_dir: Path) -> Dict[str, List[Path]]:
        """
        Export all research data in multiple formats.
        
        Returns:
            Dictionary mapping data type to list of exported file paths
        """
        log.info("Exporting all research data...")
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        exports = {}
        
        try:
            exports['runtime_curves'] = self.export_runtime_curves(output_dir / "runtime_curves")
        except Exception as e:
            log.error(f"Failed to export runtime curves: {e}")
            exports['runtime_curves'] = []
        
        try:
            exports['tle_mle_rates'] = self.export_tle_mle_rates(output_dir / "tle_mle_rates")
        except Exception as e:
            log.error(f"Failed to export TLE/MLE rates: {e}")
            exports['tle_mle_rates'] = []
        
        try:
            exports['iteration_analysis'] = self.export_iteration_analysis(output_dir / "iteration_analysis")
        except Exception as e:
            log.error(f"Failed to export iteration analysis: {e}")
            exports['iteration_analysis'] = []
        
        # Create summary file
        summary_file = output_dir / "export_summary.json"
        summary = {
            "export_timestamp": pd.Timestamp.now().isoformat(),
            "source_file": str(self.results_file),
            "total_results": len(self.results_data.get('results', [])),
            "exports": {k: [str(p) for p in v] for k, v in exports.items()},
            "total_files_exported": sum(len(v) for v in exports.values())
        }
        
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        log.info(f"Exported all research data to {output_dir}")
        log.info(f"Total files created: {summary['total_files_exported']}")
        
        return exports


def export_research_data(results_file: Path, output_dir: Path) -> Dict[str, List[Path]]:
    """
    Convenience function to export all research data.
    
    Args:
        results_file: Path to research_results_*.json file
        output_dir: Output directory for exported data
        
    Returns:
        Dictionary mapping data type to exported file paths
    """
    exporter = ResearchDataExporter(results_file)
    return exporter.export_all_research_data(output_dir)
