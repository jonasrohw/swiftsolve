"""
Statistical Analysis and Visualization

Provides DataFrame aggregation, statistical analysis, and plotting capabilities
for SwiftSolve evaluation results. Based on CONTEXT.md section 4.2 Phase D.

Generates plots and summary statistics for research publication.
"""

import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import warnings

from .metrics import EvaluationMetrics, RunMetrics
from ..utils.logger import get_logger

# Suppress matplotlib warnings
warnings.filterwarnings('ignore', category=UserWarning, module='matplotlib')

log = get_logger("EvaluationStats")


class EvaluationAnalyzer:
    """Statistical analysis and visualization for evaluation results."""
    
    def __init__(self, results_dir: Path, output_dir: Path):
        """
        Initialize analyzer.
        
        Args:
            results_dir: Directory containing evaluation result files
            output_dir: Directory to save plots and reports
        """
        self.results_dir = Path(results_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Set plot style
        plt.style.use('default')
        sns.set_palette("husl")
        
        self.all_results: List[RunMetrics] = []
        self.df: Optional[pd.DataFrame] = None
    
    def load_all_results(self) -> None:
        """Load all evaluation results from results directory."""
        log.info(f"Loading evaluation results from {self.results_dir}")
        
        self.all_results = []
        result_files = list(self.results_dir.glob("*.json"))
        
        for result_file in result_files:
            try:
                metrics = EvaluationMetrics()
                metrics.load_results(result_file)
                self.all_results.extend(metrics.results)
            except Exception as e:
                log.warning(f"Failed to load {result_file}: {e}")
        
        # Convert to DataFrame for analysis
        self.df = self._create_dataframe()
        log.info(f"Loaded {len(self.all_results)} total results from {len(result_files)} files")
    
    def _create_dataframe(self) -> pd.DataFrame:
        """Convert results to pandas DataFrame."""
        if not self.all_results:
            return pd.DataFrame()
        
        data = []
        for r in self.all_results:
            data.append({
                'task_id': r.task_id,
                'run_id': r.run_id,
                'status': r.status.value,
                'success': r.success,
                'efficient_runtime': r.efficient_runtime,
                'efficient_memory': r.efficient_memory,
                'iteration_count': r.iteration_count,
                'final_runtime_ms': r.final_runtime_ms,
                'final_memory_mb': r.final_memory_mb,
                'runtime_limit_ms': r.runtime_limit_ms,
                'memory_limit_mb': r.memory_limit_mb,
                'agent_failures': r.agent_failures,
                # Derived fields
                'runtime_ratio': (r.final_runtime_ms / r.runtime_limit_ms 
                                 if r.final_runtime_ms and r.runtime_limit_ms else None),
                'memory_ratio': (r.final_memory_mb / r.memory_limit_mb 
                                if r.final_memory_mb and r.memory_limit_mb else None),
                'task_difficulty': self._infer_difficulty(r.task_id),
                'complexity_class': self._infer_complexity(r.task_id)
            })
        
        return pd.DataFrame(data)
    
    def _infer_difficulty(self, task_id: str) -> str:
        """Infer difficulty from task ID."""
        if 'CF' in task_id:
            # Codeforces task - infer from problem index
            if task_id.endswith('A'):
                return 'easy'
            elif task_id.endswith(('B', 'C')):
                return 'medium'
            else:
                return 'hard'
        elif 'BIGOBENCH' in task_id:
            # BigO(Bench) - infer from ID number
            id_num = int(''.join(filter(str.isdigit, task_id)) or '0')
            if id_num <= 10:
                return 'easy'
            elif id_num <= 30:
                return 'medium'
            else:
                return 'hard'
        else:
            return 'medium'  # Default
    
    def _infer_complexity(self, task_id: str) -> str:
        """Infer expected complexity class from task ID."""
        if 'BIGOBENCH' in task_id:
            id_num = int(''.join(filter(str.isdigit, task_id)) or '0')
            if id_num <= 5:
                return 'O(n)'
            elif id_num <= 15:
                return 'O(n log n)'
            elif id_num <= 25:
                return 'O(n^2)'
            else:
                return 'O(n^k)'
        else:
            return 'O(n)'  # Default for Codeforces
    
    def generate_summary_stats(self) -> Dict[str, Any]:
        """Generate comprehensive summary statistics."""
        if self.df is None or self.df.empty:
            return {"error": "No data available"}
        
        # Overall metrics
        total_runs = len(self.df)
        unique_tasks = self.df['task_id'].nunique()
        success_rate = self.df['success'].mean() * 100
        
        # Efficiency metrics
        runtime_efficiency = self.df['efficient_runtime'].mean() * 100
        memory_efficiency = self.df['efficient_memory'].mean() * 100
        
        # Performance statistics
        successful_runs = self.df[self.df['success'] == True]
        
        runtime_stats = {}
        memory_stats = {}
        iteration_stats = {}
        
        if not successful_runs.empty:
            # Runtime statistics
            runtime_data = successful_runs['final_runtime_ms'].dropna()
            if not runtime_data.empty:
                runtime_stats = {
                    'mean': runtime_data.mean(),
                    'median': runtime_data.median(),
                    'std': runtime_data.std(),
                    'min': runtime_data.min(),
                    'max': runtime_data.max(),
                    'p95': runtime_data.quantile(0.95)
                }
            
            # Memory statistics
            memory_data = successful_runs['final_memory_mb'].dropna()
            if not memory_data.empty:
                memory_stats = {
                    'mean': memory_data.mean(),
                    'median': memory_data.median(),
                    'std': memory_data.std(),
                    'min': memory_data.min(),
                    'max': memory_data.max(),
                    'p95': memory_data.quantile(0.95)
                }
            
            # Iteration statistics
            iteration_data = successful_runs['iteration_count']
            iteration_stats = {
                'mean': iteration_data.mean(),
                'median': iteration_data.median(),
                'std': iteration_data.std(),
                'min': iteration_data.min(),
                'max': iteration_data.max()
            }
        
        # Breakdown by difficulty
        difficulty_breakdown = {}
        for difficulty in self.df['task_difficulty'].unique():
            subset = self.df[self.df['task_difficulty'] == difficulty]
            difficulty_breakdown[difficulty] = {
                'total_runs': len(subset),
                'success_rate': subset['success'].mean() * 100,
                'runtime_efficiency': subset['efficient_runtime'].mean() * 100,
                'memory_efficiency': subset['efficient_memory'].mean() * 100
            }
        
        # Breakdown by complexity
        complexity_breakdown = {}
        for complexity in self.df['complexity_class'].unique():
            subset = self.df[self.df['complexity_class'] == complexity]
            complexity_breakdown[complexity] = {
                'total_runs': len(subset),
                'success_rate': subset['success'].mean() * 100,
                'runtime_efficiency': subset['efficient_runtime'].mean() * 100,
                'memory_efficiency': subset['efficient_memory'].mean() * 100
            }
        
        return {
            'overall_metrics': {
                'total_runs': total_runs,
                'unique_tasks': unique_tasks,
                'success_rate_percent': success_rate,
                'runtime_efficiency_percent': runtime_efficiency,
                'memory_efficiency_percent': memory_efficiency
            },
            'performance_statistics': {
                'runtime_ms': runtime_stats,
                'memory_mb': memory_stats,
                'iterations': iteration_stats
            },
            'breakdown_by_difficulty': difficulty_breakdown,
            'breakdown_by_complexity': complexity_breakdown
        }
    
    def plot_success_rates(self) -> Path:
        """Plot success rates by difficulty and complexity."""
        if self.df is None or self.df.empty:
            log.warning("No data available for plotting")
            return None
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        # Success rate by difficulty
        difficulty_success = self.df.groupby('task_difficulty')['success'].mean() * 100
        difficulty_success.plot(kind='bar', ax=ax1, color='skyblue')
        ax1.set_title('Success Rate by Difficulty')
        ax1.set_ylabel('Success Rate (%)')
        ax1.set_xlabel('Difficulty')
        ax1.tick_params(axis='x', rotation=45)
        
        # Success rate by complexity
        complexity_success = self.df.groupby('complexity_class')['success'].mean() * 100
        complexity_success.plot(kind='bar', ax=ax2, color='lightcoral')
        ax2.set_title('Success Rate by Complexity Class')
        ax2.set_ylabel('Success Rate (%)')
        ax2.set_xlabel('Complexity Class')
        ax2.tick_params(axis='x', rotation=45)
        
        plt.tight_layout()
        output_path = self.output_dir / "success_rates.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        log.info(f"Saved success rates plot to {output_path}")
        return output_path
    
    def plot_performance_distributions(self) -> Path:
        """Plot runtime and memory performance distributions."""
        if self.df is None or self.df.empty:
            log.warning("No data available for plotting")
            return None
        
        successful_runs = self.df[self.df['success'] == True]
        
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 12))
        
        # Runtime distribution
        runtime_data = successful_runs['final_runtime_ms'].dropna()
        if not runtime_data.empty:
            ax1.hist(runtime_data, bins=30, alpha=0.7, color='skyblue')
            ax1.set_title('Runtime Distribution (Successful Runs)')
            ax1.set_xlabel('Runtime (ms)')
            ax1.set_ylabel('Frequency')
            ax1.axvline(runtime_data.mean(), color='red', linestyle='--', label=f'Mean: {runtime_data.mean():.1f}ms')
            ax1.legend()
        
        # Memory distribution
        memory_data = successful_runs['final_memory_mb'].dropna()
        if not memory_data.empty:
            ax2.hist(memory_data, bins=30, alpha=0.7, color='lightcoral')
            ax2.set_title('Memory Usage Distribution (Successful Runs)')
            ax2.set_xlabel('Memory (MB)')
            ax2.set_ylabel('Frequency')
            ax2.axvline(memory_data.mean(), color='red', linestyle='--', label=f'Mean: {memory_data.mean():.1f}MB')
            ax2.legend()
        
        # Runtime vs Memory scatter
        if not runtime_data.empty and not memory_data.empty:
            valid_data = successful_runs[['final_runtime_ms', 'final_memory_mb']].dropna()
            if not valid_data.empty:
                ax3.scatter(valid_data['final_runtime_ms'], valid_data['final_memory_mb'], alpha=0.6)
                ax3.set_title('Runtime vs Memory Usage')
                ax3.set_xlabel('Runtime (ms)')
                ax3.set_ylabel('Memory (MB)')
        
        # Iteration count distribution
        iteration_data = successful_runs['iteration_count']
        ax4.hist(iteration_data, bins=range(1, int(iteration_data.max()) + 2), alpha=0.7, color='lightgreen')
        ax4.set_title('Iteration Count Distribution (Successful Runs)')
        ax4.set_xlabel('Iterations to Success')
        ax4.set_ylabel('Frequency')
        ax4.axvline(iteration_data.mean(), color='red', linestyle='--', label=f'Mean: {iteration_data.mean():.1f}')
        ax4.legend()
        
        plt.tight_layout()
        output_path = self.output_dir / "performance_distributions.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        log.info(f"Saved performance distributions plot to {output_path}")
        return output_path
    
    def plot_efficiency_analysis(self) -> Path:
        """Plot efficiency analysis (runtime/memory vs limits)."""
        if self.df is None or self.df.empty:
            log.warning("No data available for plotting")
            return None
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        # Runtime efficiency
        runtime_data = self.df[['runtime_ratio', 'success']].dropna()
        if not runtime_data.empty:
            successful = runtime_data[runtime_data['success'] == True]['runtime_ratio']
            failed = runtime_data[runtime_data['success'] == False]['runtime_ratio']
            
            ax1.hist(successful, bins=30, alpha=0.7, label='Successful', color='green')
            ax1.hist(failed, bins=30, alpha=0.7, label='Failed', color='red')
            ax1.axvline(1.0, color='black', linestyle='--', label='Time Limit')
            ax1.set_title('Runtime Efficiency (Runtime/Limit Ratio)')
            ax1.set_xlabel('Runtime Ratio')
            ax1.set_ylabel('Frequency')
            ax1.legend()
        
        # Memory efficiency
        memory_data = self.df[['memory_ratio', 'success']].dropna()
        if not memory_data.empty:
            successful = memory_data[memory_data['success'] == True]['memory_ratio']
            failed = memory_data[memory_data['success'] == False]['memory_ratio']
            
            ax2.hist(successful, bins=30, alpha=0.7, label='Successful', color='green')
            ax2.hist(failed, bins=30, alpha=0.7, label='Failed', color='red')
            ax2.axvline(1.0, color='black', linestyle='--', label='Memory Limit')
            ax2.set_title('Memory Efficiency (Memory/Limit Ratio)')
            ax2.set_xlabel('Memory Ratio')
            ax2.set_ylabel('Frequency')
            ax2.legend()
        
        plt.tight_layout()
        output_path = self.output_dir / "efficiency_analysis.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        log.info(f"Saved efficiency analysis plot to {output_path}")
        return output_path
    
    def generate_markdown_report(self) -> Path:
        """Generate comprehensive Markdown report."""
        stats = self.generate_summary_stats()
        
        report_lines = [
            "# SwiftSolve Evaluation Report",
            "",
            "## Overview",
            f"- **Total Runs**: {stats['overall_metrics']['total_runs']}",
            f"- **Unique Tasks**: {stats['overall_metrics']['unique_tasks']}",
            f"- **Success Rate**: {stats['overall_metrics']['success_rate_percent']:.1f}%",
            f"- **Runtime Efficiency**: {stats['overall_metrics']['runtime_efficiency_percent']:.1f}%",
            f"- **Memory Efficiency**: {stats['overall_metrics']['memory_efficiency_percent']:.1f}%",
            "",
            "## Performance Statistics",
            "",
            "### Runtime (Successful Runs)",
            f"- Mean: {stats['performance_statistics']['runtime_ms'].get('mean', 0):.1f} ms",
            f"- Median: {stats['performance_statistics']['runtime_ms'].get('median', 0):.1f} ms",
            f"- 95th Percentile: {stats['performance_statistics']['runtime_ms'].get('p95', 0):.1f} ms",
            "",
            "### Memory (Successful Runs)",
            f"- Mean: {stats['performance_statistics']['memory_mb'].get('mean', 0):.1f} MB",
            f"- Median: {stats['performance_statistics']['memory_mb'].get('median', 0):.1f} MB", 
            f"- 95th Percentile: {stats['performance_statistics']['memory_mb'].get('p95', 0):.1f} MB",
            "",
            "### Convergence",
            f"- Mean Iterations to Success: {stats['performance_statistics']['iterations'].get('mean', 0):.1f}",
            f"- Median Iterations: {stats['performance_statistics']['iterations'].get('median', 0):.1f}",
            "",
            "## Results by Difficulty",
            ""
        ]
        
        # Add difficulty breakdown
        for difficulty, metrics in stats['breakdown_by_difficulty'].items():
            report_lines.extend([
                f"### {difficulty.title()}",
                f"- Total Runs: {metrics['total_runs']}",
                f"- Success Rate: {metrics['success_rate']:.1f}%",
                f"- Runtime Efficiency: {metrics['runtime_efficiency']:.1f}%",
                f"- Memory Efficiency: {metrics['memory_efficiency']:.1f}%",
                ""
            ])
        
        # Add complexity breakdown
        report_lines.extend([
            "## Results by Complexity Class",
            ""
        ])
        
        for complexity, metrics in stats['breakdown_by_complexity'].items():
            report_lines.extend([
                f"### {complexity}",
                f"- Total Runs: {metrics['total_runs']}",
                f"- Success Rate: {metrics['success_rate']:.1f}%",
                f"- Runtime Efficiency: {metrics['runtime_efficiency']:.1f}%",
                f"- Memory Efficiency: {metrics['memory_efficiency']:.1f}%",
                ""
            ])
        
        report_content = "\n".join(report_lines)
        
        output_path = self.output_dir / "evaluation_report.md"
        with open(output_path, 'w') as f:
            f.write(report_content)
        
        log.info(f"Generated Markdown report: {output_path}")
        return output_path
    
    def generate_csv_summary(self) -> Path:
        """Generate CSV summary for external analysis."""
        if self.df is None or self.df.empty:
            log.warning("No data available for CSV export")
            return None
        
        # Create summary by task
        task_summary = self.df.groupby('task_id').agg({
            'success': ['count', 'sum', 'mean'],
            'efficient_runtime': 'mean',
            'efficient_memory': 'mean',
            'iteration_count': 'mean',
            'final_runtime_ms': 'mean',
            'final_memory_mb': 'mean',
            'task_difficulty': 'first',
            'complexity_class': 'first'
        }).round(3)
        
        # Flatten column names
        task_summary.columns = ['_'.join(col).strip() for col in task_summary.columns]
        task_summary = task_summary.rename(columns={
            'success_count': 'total_runs',
            'success_sum': 'successful_runs',
            'success_mean': 'success_rate',
            'efficient_runtime_mean': 'runtime_efficiency',
            'efficient_memory_mean': 'memory_efficiency',
            'iteration_count_mean': 'mean_iterations',
            'final_runtime_ms_mean': 'mean_runtime_ms',
            'final_memory_mb_mean': 'mean_memory_mb',
            'task_difficulty_first': 'difficulty',
            'complexity_class_first': 'complexity'
        })
        
        output_path = self.output_dir / "task_summary.csv"
        task_summary.to_csv(output_path)
        
        log.info(f"Generated CSV summary: {output_path}")
        return output_path
    
    def generate_full_report(self) -> Dict[str, Path]:
        """Generate complete evaluation report with all outputs."""
        log.info("Generating comprehensive evaluation report")
        
        if self.df is None or self.df.empty:
            log.error("No data loaded for report generation")
            return {}
        
        outputs = {}
        
        # Generate plots
        try:
            outputs['success_plot'] = self.plot_success_rates()
            outputs['performance_plot'] = self.plot_performance_distributions()
            outputs['efficiency_plot'] = self.plot_efficiency_analysis()
        except Exception as e:
            log.warning(f"Plot generation failed: {e}")
        
        # Generate reports
        try:
            outputs['markdown_report'] = self.generate_markdown_report()
            outputs['csv_summary'] = self.generate_csv_summary()
        except Exception as e:
            log.warning(f"Report generation failed: {e}")
        
        # Save raw statistics
        try:
            stats = self.generate_summary_stats()
            stats_path = self.output_dir / "summary_statistics.json"
            with open(stats_path, 'w') as f:
                json.dump(stats, f, indent=2)
            outputs['statistics'] = stats_path
        except Exception as e:
            log.warning(f"Statistics export failed: {e}")
        
        log.info(f"Generated evaluation report with {len(outputs)} components")
        return outputs


if __name__ == "__main__":
    # Test with sample data
    analyzer = EvaluationAnalyzer(Path("results"), Path("reports"))
    
    # Would normally call: analyzer.load_all_results()
    # For testing, create sample data
    from .metrics import create_sample_evaluation
    sample_metrics = create_sample_evaluation()
    analyzer.all_results = sample_metrics.results
    analyzer.df = analyzer._create_dataframe()
    
    outputs = analyzer.generate_full_report()
    print(f"Generated report components: {list(outputs.keys())}")