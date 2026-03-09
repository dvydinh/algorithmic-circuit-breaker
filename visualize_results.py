#!/usr/bin/env python3
"""
Visualization Dashboard for Circuit Breaker Simulation
=======================================================
Creates a professional 3-panel visualization of simulation results.

Usage:
    python visualize_results.py
    python visualize_results.py --input output/simulation_log.csv --output my_chart.png
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import argparse
from pathlib import Path
import sys
import os

# Add path so we can import the core config
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from circuit_breaker.core.config import PIDConfig


def load_data(filepath: str) -> pd.DataFrame:
    """Load simulation log from CSV."""
    df = pd.read_csv(filepath)
    # Convert simulated time to minutes for readability
    df['time_min'] = df['simulated_time_sec'] / 60.0
    return df


def create_dashboard(df: pd.DataFrame, output_path: str, threshold: float = 0.35):
    """
    Create a professional 3-panel dashboard.
    
    Panels:
    1. Top: Dopamine Level vs Baseline with Break events
    2. Middle: PID Control Signal & Risk Index with Threshold
    3. Bottom: Scroll Velocity (clicks per minute)
    """
    # Use seaborn style for professional look
    plt.style.use('seaborn-v0_8-whitegrid')
    
    # Create figure with 3 subplots
    fig, axes = plt.subplots(3, 1, figsize=(14, 10), sharex=True)
    fig.suptitle('Algorithmic Circuit Breaker - Simulation Dashboard', 
                 fontsize=16, fontweight='bold', y=0.98)
    
    # Color palette
    colors = {
        'dopamine': '#2ecc71',       # Green
        'baseline': '#27ae60',       # Dark green (dashed)
        'risk': '#e74c3c',           # Red
        'control': '#3498db',        # Blue
        'velocity': '#9b59b6',       # Purple
        'threshold': '#f39c12',      # Orange
        'break': '#c0392b',          # Dark red
        'friction': '#f1c40f',       # Yellow
        'reroute': '#e67e22',        # Orange
    }
    
    time = df['time_min']
    
    # ============ PANEL 1: Dopamine Level ============
    ax1 = axes[0]
    
    # Plot dopamine level
    ax1.plot(time, df['dopamine_level'], 
             color=colors['dopamine'], linewidth=1.5, label='Dopamine Level', alpha=0.9)
    
    # Plot baseline (dashed)
    ax1.plot(time, df['dopamine_baseline'], 
             color=colors['baseline'], linewidth=1.5, linestyle='--', 
             label='Dopamine Baseline', alpha=0.7)
    
    # Mark Break events with red translucent shaded regions
    break_mask = df['intervention_type'] == 'break'
    if break_mask.any():
        ax1.fill_between(time, 0, 1.05, where=break_mask, 
                         color=colors['break'], alpha=0.15, label='Break Active')
    
    # Mark Friction zones (light yellow background)
    friction_mask = df['intervention_type'] == 'friction'
    if friction_mask.any():
        ax1.fill_between(time, 0, 1, where=friction_mask, 
                        color=colors['friction'], alpha=0.15, label='Friction Active')
    
    ax1.set_ylabel('Dopamine Level', fontsize=11, fontweight='bold')
    ax1.set_ylim(0, 1.05)
    ax1.legend(loc='upper right', fontsize=9)
    ax1.set_title('User Dopamine Dynamics', fontsize=12, pad=10)
    
    # Add tolerance as secondary y-axis
    ax1_twin = ax1.twinx()
    ax1_twin.plot(time, df['tolerance'], color='#8e44ad', linewidth=1, 
                  linestyle=':', alpha=0.6, label='Tolerance')
    ax1_twin.set_ylabel('Tolerance', fontsize=10, color='#8e44ad')
    ax1_twin.tick_params(axis='y', labelcolor='#8e44ad')
    ax1_twin.set_ylim(0, 1.05)
    
    # ============ PANEL 2: PID Control Signal & Risk Index ============
    ax2 = axes[1]
    
    # Plot Risk Index
    ax2.plot(time, df['risk_index'], 
             color=colors['risk'], linewidth=1.5, label='Risk Index', alpha=0.8)
    
    # Plot Control Signal
    ax2.plot(time, df['control_signal_u'], 
             color=colors['control'], linewidth=1.5, label='Control Signal u(t)', alpha=0.9)
    
    # Plot Threshold line
    ax2.axhline(y=threshold, color=colors['threshold'], linewidth=2, 
               linestyle='--', label=f'Threshold ({threshold})', alpha=0.8)
    
    # Add intervention threshold lines
    ax2.axhline(y=0.2, color='#95a5a6', linewidth=1, linestyle=':', alpha=0.5)
    ax2.axhline(y=0.4, color='#95a5a6', linewidth=1, linestyle=':', alpha=0.5)
    ax2.axhline(y=0.6, color='#95a5a6', linewidth=1, linestyle=':', alpha=0.5)
    
    # Annotate threshold zones
    ax2.text(time.max() * 1.01, 0.1, 'NONE', fontsize=8, color='#27ae60', va='center')
    ax2.text(time.max() * 1.01, 0.3, 'FRICTION', fontsize=8, color='#f39c12', va='center')
    ax2.text(time.max() * 1.01, 0.5, 'REROUTE', fontsize=8, color='#e67e22', va='center')
    ax2.text(time.max() * 1.01, 0.7, 'BREAK', fontsize=8, color='#c0392b', va='center')
    
    ax2.set_ylabel('Signal Value', fontsize=11, fontweight='bold')
    ax2.set_ylim(0, 1.0)
    ax2.legend(loc='upper left', fontsize=9)
    ax2.set_title('PID Controller: Risk Index & Control Signal', fontsize=12, pad=10)
    
    # ============ PANEL 3: Scroll Velocity ============
    ax3 = axes[2]
    
    # Plot velocity
    ax3.fill_between(time, 0, df['velocity_clicks_per_min'], 
                    color=colors['velocity'], alpha=0.4)
    ax3.plot(time, df['velocity_clicks_per_min'], 
             color=colors['velocity'], linewidth=1.5, label='Clicks/min')
    
    # Add rolling average for smoothing
    if len(df) > 10:
        rolling_velocity = df['velocity_clicks_per_min'].rolling(window=10, min_periods=1).mean()
        ax3.plot(time, rolling_velocity, color='#2c3e50', linewidth=2, 
                linestyle='--', label='Rolling Avg (10)', alpha=0.7)
    
    ax3.set_ylabel('Clicks per Minute', fontsize=11, fontweight='bold')
    ax3.set_xlabel('Simulated Time (minutes)', fontsize=11, fontweight='bold')
    ax3.set_ylim(0, max(df['velocity_clicks_per_min'].max() * 1.1, 10))
    ax3.legend(loc='upper right', fontsize=9)
    ax3.set_title('User Engagement Velocity', fontsize=12, pad=10)
    
    # ============ Final Styling ============
    # Enforce strictly physical limits (no negative time margins)
    for ax in axes:
        ax.set_xlim(left=0)
        
    # Adjust layout
    plt.tight_layout()
    fig.subplots_adjust(top=0.93, hspace=0.15)
    
    # Add summary stats as text box
    summary_text = (
        f"Total Steps: {len(df)} | "
        f"Duration: {df['time_min'].max():.1f} min | "
        f"Clicks: {(df['interaction_type'] == 'click').sum()} | "
        f"Avg Dopamine: {df['dopamine_level'].mean():.2f}"
    )
    fig.text(0.5, 0.01, summary_text, ha='center', fontsize=10, 
            style='italic', color='#7f8c8d')
    
    # Save figure
    plt.savefig(output_path, dpi=150, bbox_inches='tight', 
                facecolor='white', edgecolor='none')
    print(f"Dashboard saved to: {output_path}")
    
    # Also show if running interactively
    plt.show()


def main():
    parser = argparse.ArgumentParser(
        description='Visualize Circuit Breaker simulation results'
    )
    parser.add_argument(
        '--input', '-i',
        type=str,
        default='output/simulation_log.csv',
        help='Input CSV file path (default: output/simulation_log.csv)'
    )
    parser.add_argument(
        '--output', '-o',
        type=str,
        default='simulation_result.png',
        help='Output image file path (default: simulation_result.png)'
    )
    default_threshold = PIDConfig().circuit_break_threshold
    
    parser.add_argument(
        '--threshold', '-t',
        type=float,
        default=default_threshold,
        help=f'Risk threshold for display (default: {default_threshold})'
    )
    
    args = parser.parse_args()
    
    # Check input file exists
    if not Path(args.input).exists():
        print(f"Error: Input file '{args.input}' not found.")
        print("Run 'python run_simulation.py' first to generate data.")
        return
    
    # Load and visualize
    print(f"Loading data from: {args.input}")
    df = load_data(args.input)
    print(f"Loaded {len(df)} rows, {df['time_min'].max():.1f} minutes of simulated time")
    
    create_dashboard(df, args.output, args.threshold)


if __name__ == "__main__":
    main()
