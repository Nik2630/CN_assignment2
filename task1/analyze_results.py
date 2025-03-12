import os
import json
import matplotlib.pyplot as plt
import numpy as np
import subprocess
from scapy.all import rdpcap, TCP
import argparse

def retrieve_throughput_data(source_file):
    """Extracts and organizes throughput metrics from iperf3 JSON output."""
    try:
        with open(source_file, 'r') as descriptor:
            raw_data = json.load(descriptor)
            analysis_result = {
                'time_points': [],
                'bandwidth_values': [],
                'achieved_goodput': 0,
                'packet_drop_ratio': 0,
                'resend_count': 0
            }

            if 'intervals' in raw_data and raw_data['intervals']:
                data_segments = raw_data['intervals']
                index = 0
                while index < len(data_segments):
                    segment = data_segments[index]
                    analysis_result['time_points'].append(segment['sum']['start'])
                    analysis_result['bandwidth_values'].append(segment['sum']['bits_per_second'] / 1000000.0)
                    index += 1

            if 'end' in raw_data:
                final_summary = raw_data['end']
                if 'sum_sent' in final_summary:
                    transmit_summary = final_summary['sum_sent']
                    analysis_result['resend_count'] = transmit_summary.get('retransmits', 0)

                    total_bytes_sent = transmit_summary.get('bytes', 0)
                    duration_seconds = transmit_summary.get('seconds', 0)

                    if duration_seconds > 0:
                        analysis_result['achieved_goodput'] = (total_bytes_sent * 8.0) / duration_seconds / 1000000.0
                    else:
                        analysis_result['achieved_goodput'] = transmit_summary.get('bits_per_second', 0) / 1000000.0

                if 'sum' in final_summary:
                    overall_summary = final_summary['sum']
                    if 'lost_packets' in overall_summary and 'packets' in overall_summary and overall_summary['packets'] > 0:
                        analysis_result['packet_drop_ratio'] = (overall_summary['lost_packets'] / overall_summary['packets']) * 100.0

            if analysis_result['achieved_goodput'] > 0 and not analysis_result['time_points']:
                analysis_result['time_points'] = [0]
                analysis_result['bandwidth_values'] = [analysis_result['achieved_goodput']]

            return analysis_result

    except json.JSONDecodeError:
        print(f"Warning: Incompatible JSON format in '{source_file}'.")
        return None
    except Exception as error_message:
        print(f"Issue encountered while processing '{source_file}': {error_message}")
        return None

def examine_pcap_data(pcap_filepath):
    """Analyzes a PCAP file to extract TCP window size information."""
    try:
        packet_stream = rdpcap(pcap_filepath)
        timestamps = []
        tcp_windows = []
        packet_index = 0

        while packet_index < len(packet_stream):
            packet = packet_stream[packet_index]
            if TCP in packet:
                timestamps.append(packet.time - packet_stream[0].time)
                tcp_windows.append(packet[TCP].window)
            packet_index += 1

        maximum_window = max(tcp_windows) if tcp_windows else 0

        return {
            'time_sequence': timestamps,
            'window_sizes_sequence': tcp_windows,
            'peak_window_size': maximum_window
        }
    except Exception as error_detail:
        print(f"Problem during PCAP analysis '{pcap_filepath}': {error_detail}")
        return None

def generate_throughput_graph(results_directory, algorithms_list):
    """Generates and saves a graph of throughput over time for different algorithms."""
    figure_handle, axis_handle = plt.subplots(figsize=(10, 6))
    data_present = False

    for algorithm_name in algorithms_list:
        candidate_files = [
            os.path.join(results_directory, f'h1_h7_{algorithm_name}.json'),
            os.path.join(results_directory, f'iperf3_h1_to_h7_{algorithm_name}.json')
        ]

        file_found = False
        for current_file_path in candidate_files:
            if os.path.isfile(current_file_path):
                parsed_data = retrieve_throughput_data(current_file_path)
                if parsed_data and parsed_data['time_points'] and parsed_data['bandwidth_values']:
                    axis_handle.plot(parsed_data['time_points'], parsed_data['bandwidth_values'], label=algorithm_name)
                    data_present = True
                    file_found = True
                    break
        if not file_found:
            continue

    if not data_present:
        print(f"Warning: No valid throughput data located in '{results_directory}'.")
        plt.close(figure_handle)
        return

    axis_handle.set_xlabel('Time (seconds)')
    axis_handle.set_ylabel('Throughput (Mbps)')
    axis_handle.set_title('Throughput Progression')
    axis_handle.legend()
    axis_handle.grid(True)

    output_graph_file = os.path.join(results_directory, 'throughput_comparison.png')
    figure_handle.savefig(output_graph_file)
    plt.close(figure_handle)
    print(f"Throughput graph saved to '{output_graph_file}'.")

def generate_window_size_graph(results_directory, algorithms_list):
    """Produces a graph of TCP window size over time for various congestion algorithms."""
    figure_instance, axis_instance = plt.subplots(figsize=(10, 6))
    data_available = False

    for algorithm_variant in algorithms_list:
        potential_files = [
            os.path.join(results_directory, f'h1_h7_{algorithm_variant}.pcap'),
            os.path.join(results_directory, f'h1_h7_{algorithm_variant}.pcap')
        ]

        valid_file_path = None
        for path in potential_files:
            if os.path.isfile(path):
                valid_file_path = path
                break

        if valid_file_path:
            extracted_data = examine_pcap_data(valid_file_path)
            if extracted_data and extracted_data['time_sequence'] and extracted_data['window_sizes_sequence']:
                time_values = extracted_data['time_sequence']
                window_values = extracted_data['window_sizes_sequence']

                if len(time_values) > 1000:
                    sample_indices = np.linspace(0, len(time_values)-1, 1000, dtype=int)
                    time_values = [time_values[i] for i in sample_indices]
                    window_values = [window_values[i] for i in sample_indices]

                axis_instance.plot(time_values, window_values, label=f"{algorithm_variant} (max: {extracted_data['peak_window_size']})")
                data_available = True

    if not data_available:
        print(f"Warning: No valid window size information found in '{results_directory}'.")
        plt.close(figure_instance)
        return

    axis_instance.set_xlabel('Time (seconds)')
    axis_instance.set_ylabel('Window Size (bytes)')
    axis_instance.set_title('TCP Window Size Evolution')
    axis_instance.legend()
    axis_instance.grid(True)

    output_graph_location = os.path.join(results_directory, 'window_size_comparison.png')
    figure_instance.savefig(output_graph_location)
    plt.close(figure_instance)
    print(f"Window size graph saved to '{output_graph_location}'.")

def generate_summary_report(results_folder, algorithm_options):
    """Generates a summary table of experiment results."""
    report_data = []

    for algorithm_type in algorithm_options:
        possible_data_files = [
            os.path.join(results_folder, f'h1_h7_{algorithm_type}.json'),
            os.path.join(results_folder, f'iperf3_h1_to_h7_{algorithm_type}.json')
        ]

        json_file_path = next((path for path in possible_data_files if os.path.isfile(path)), None)

        if json_file_path:
            throughput_metrics = retrieve_throughput_data(json_file_path)
            if throughput_metrics:
                pcap_search_paths = [
                    os.path.join(results_folder, f'h1_h7_{algorithm_type}.pcap'),
                    os.path.join(results_folder, f'h1_h7_{algorithm_type}.pcap')
                ]

                window_stats = {'peak_window_size': 'N/A'}
                for pcap_path in pcap_search_paths:
                    if os.path.isfile(pcap_path):
                        window_stats = examine_pcap_data(pcap_path)
                        break

                report_data.append({
                    'Algorithm': algorithm_type,
                    'Goodput (Mbps)': f"{throughput_metrics['achieved_goodput']:.2f}",
                    'Packet Loss (%)': f"{throughput_metrics['packet_drop_ratio']:.2f}",
                    'Max Window Size': window_stats['peak_window_size'],
                    'Retransmits': throughput_metrics['resend_count']
                })

    if report_data:
        print("\nExperiment Results Summary:")
        print("-" * 80)
        header_keys = report_data[0].keys()
        print(f"{'Algorithm':<10} {'Goodput (Mbps)':<15} {'Packet Loss (%)':<15} {'Max Window Size':<15} {'Retransmits':<10}")
        print("-" * 80)
        for record in report_data:
            print(f"{record['Algorithm']:<10} {record['Goodput (Mbps)']:<15} {record['Packet Loss (%)']:<15} {str(record['Max Window Size']):<15} {record['Retransmits']:<10}")
        print("-" * 80)

        summary_file_location = os.path.join(results_folder, 'summary.txt')
        with open(summary_file_location, 'w') as output_file:
            output_file.write("Experiment Results Summary:\n")
            output_file.write("-" * 80 + "\n")
            output_file.write(f"{'Algorithm':<10} {'Goodput (Mbps)':<15} {'Packet Loss (%)':<15} {'Max Window Size':<15} {'Retransmits':<10}\n")
            output_file.write("-" * 80 + "\n")
            for record in report_data:
                output_file.write(f"{record['Algorithm']:<10} {record['Goodput (Mbps)']:<15} {record['Packet Loss (%)']:<15} {str(record['Max Window Size']):<15} {record['Retransmits']:<10}\n")
            output_file.write("-" * 80 + "\n")
        print(f"Summary report saved to '{summary_file_location}'.")

def analyze_staggered_start_experiment(base_directory, algorithm_variations):
    """Analyzes and visualizes results from the staggered client experiment."""
    print(f"\nAnalyzing staggered client experiment results in '{base_directory}'.")

    client_identifiers = ['h1', 'h3', 'h4']
    client_start_times = [0, 15, 30]
    client_durations = [150, 120, 90]

    for algorithm_type in algorithm_variations:
        figure_handle, axis_handle = plt.subplots(figsize=(12, 6))

        for index, client_id in enumerate(client_identifiers):
            data_file_path = os.path.join(base_directory, f'{client_id}_staggered_{algorithm_type}.json')
            if os.path.isfile(data_file_path):
                parsed_data = retrieve_throughput_data(data_file_path)
                if parsed_data and parsed_data['time_points'] and parsed_data['bandwidth_values']:
                    adjusted_time_axis = [t + client_start_times[index] for t in parsed_data['time_points']]
                    axis_handle.plot(adjusted_time_axis, parsed_data['bandwidth_values'], label=f'{client_id} (start: {client_start_times[index]}s)')

        axis_handle.set_xlabel('Time (seconds)')
        axis_handle.set_ylabel('Throughput (Mbps)')
        axis_handle.set_title(f'Staggered Client Throughput with {algorithm_type.upper()}')
        axis_handle.legend()
        axis_handle.grid(True)

        for index, client_id in enumerate(client_identifiers):
            axis_handle.axvline(x=client_start_times[index], color='r', linestyle='--', alpha=0.3)
            axis_handle.axvline(x=client_start_times[index] + client_durations[index], color='g', linestyle='--', alpha=0.3)

        output_figure_path = os.path.join(base_directory, f'staggered_{algorithm_type}_comparison.png')
        figure_handle.savefig(output_figure_path)
        plt.close(figure_handle)
        print(f"Staggered client throughput graph for {algorithm_type} saved to '{output_figure_path}'.")

    figure_instance_window, axis_instance_window = plt.subplots(figsize=(12, 6))

    for algorithm_variant in algorithm_variations:
        pcap_trace_file = os.path.join(base_directory, f'staggered_{algorithm_variant}.pcap')
        if os.path.isfile(pcap_trace_file):
            parsed_pcap_data = examine_pcap_data(pcap_trace_file)
            if parsed_pcap_data and parsed_pcap_data['time_sequence'] and parsed_pcap_data['window_sizes_sequence']:
                time_values = parsed_pcap_data['time_sequence']
                window_values = parsed_pcap_data['window_sizes_sequence']

                if len(time_values) > 1000:
                    sample_points = np.linspace(0, len(time_values)-1, 1000, dtype=int)
                    time_values = [time_values[i] for i in sample_points]
                    window_values = [window_values[i] for i in sample_points]

                axis_instance_window.plot(time_values, window_values, label=f"{algorithm_variant}")

    axis_instance_window.set_xlabel('Time (seconds)')
    axis_instance_window.set_ylabel('TCP Window Size (bytes)')
    axis_instance_window.set_title('Window Size Evolution for Staggered Clients')
    axis_instance_window.legend()
    axis_instance_window.grid(True)
    output_window_figure = os.path.join(base_directory, 'staggered_window_comparison.png')
    figure_instance_window.savefig(output_window_figure)
    plt.close(figure_instance_window)
    print(f"Staggered window size comparison graph saved to '{output_window_figure}'.")

    summary_data_staggered = []
    for algorithm_option in algorithm_variations:
        for client_identity in client_identifiers:
            json_data_path = os.path.join(base_directory, f'{client_identity}_staggered_{algorithm_option}.json')
            if os.path.isfile(json_data_path):
                data_metrics = retrieve_throughput_data(json_data_path)
                if data_metrics:
                    summary_data_staggered.append({
                        'Algorithm': algorithm_option,
                        'Client': client_identity,
                        'Goodput (Mbps)': f"{data_metrics['achieved_goodput']:.2f}",
                        'Retransmits': data_metrics['resend_count'],
                        'Packet Loss (%)': f"{data_metrics['packet_drop_ratio']:.2f}"
                    })

    if summary_data_staggered:
        summary_staggered_file = os.path.join(base_directory, 'staggered_summary.txt')
        with open(summary_staggered_file, 'w') as summary_output:
            summary_output.write("Staggered Clients Experiment Summary:\n")
            summary_output.write("-" * 80 + "\n")
            summary_output.write(f"{'Algorithm':<10} {'Client':<6} {'Goodput (Mbps)':<15} {'Retransmits':<12} {'Packet Loss (%)':<15}\n")
            summary_output.write("-" * 80 + "\n")

            for row_data in summary_data_staggered:
                summary_output.write(f"{row_data['Algorithm']:<10} {row_data['Client']:<6} {row_data['Goodput (Mbps)']:<15} {row_data['Retransmits']:<12} {row_data['Packet Loss (%)']:<15}\n")
                print(f"{row_data['Algorithm']:<10} {row_data['Client']:<6} {row_data['Goodput (Mbps)']:<15} {row_data['Retransmits']:<12} {row_data['Packet Loss (%)']:<15}")

            summary_output.write("-" * 80 + "\n")
        print(f"Staggered experiment summary saved to '{summary_staggered_file}'.")

def analyze_bandwidth_variation_experiment(results_location, algorithm_choices):
    """Analyzes results from the custom bandwidth experiment scenarios."""
    print(f"\nAnalyzing custom bandwidth experiment results in '{results_location}'.")

    experiment_phases = {
        'c1': ['h3'],
        'c2a': ['h1', 'h2'],
        'c2b': ['h1', 'h3'],
        'c2c': ['h1', 'h3', 'h4']
    }

    figure_goodput_comparison, axis_goodput_comparison = plt.subplots(figsize=(15, 8))
    phase_labels = ['C-I', 'C-II-a', 'C-II-b', 'C-II-c']
    x_positions = np.arange(len(phase_labels))
    bar_width = 0.2
    bar_offsets = [-bar_width, 0, bar_width]

    for algo_index, algo_name in enumerate(algorithm_choices):
        average_goodputs = []

        for phase_code, phase_clients in experiment_phases.items():
            total_phase_goodput = 0
            active_client_count = 0

            for client_name in phase_clients:
                data_file_path = os.path.join(results_location, f'{client_name}_{phase_code}_{algo_name}.json')
                if os.path.isfile(data_file_path):
                    data_metrics = retrieve_throughput_data(data_file_path)
                    if data_metrics:
                        total_phase_goodput += data_metrics['achieved_goodput']
                        active_client_count += 1

            phase_average_goodput = total_phase_goodput / active_client_count if active_client_count > 0 else 0
            average_goodputs.append(phase_average_goodput)

        axis_goodput_comparison.bar(x_positions + bar_offsets[algo_index], average_goodputs, bar_width, label=algo_name)

    axis_goodput_comparison.set_xlabel('Experiment Configuration')
    axis_goodput_comparison.set_ylabel('Average Goodput per Client (Mbps)')
    axis_goodput_comparison.set_title('Goodput Variation Across Bandwidth Scenarios')
    axis_goodput_comparison.set_xticks(x_positions)
    axis_goodput_comparison.set_xticklabels(phase_labels)
    axis_goodput_comparison.legend()
    axis_goodput_comparison.grid(axis='y')

    output_goodput_graph = os.path.join(results_location, 'bandwidth_goodput_comparison.png')
    figure_goodput_comparison.savefig(output_goodput_graph)
    plt.close(figure_goodput_comparison)
    print(f"Bandwidth comparison graph saved to '{output_goodput_graph}'.")

    for phase_code, clients_in_phase in experiment_phases.items():
        for algorithm_variant in algorithm_choices:
            figure_client_throughput, axis_client_throughput = plt.subplots(figsize=(10, 6))
            pcap_trace_file = os.path.join(results_location, f'{phase_code}_{algorithm_variant}.pcap')
            if os.path.isfile(pcap_trace_file):
                for client_identity in clients_in_phase:
                    client_json_file = os.path.join(results_location, f'{client_identity}_{phase_code}_{algorithm_variant}.json')
                    if os.path.isfile(client_json_file):
                        client_data = retrieve_throughput_data(client_json_file)
                        if client_data and client_data['time_points'] and client_data['bandwidth_values']:
                            axis_client_throughput.plot(client_data['time_points'], client_data['bandwidth_values'], label=f'{client_identity} throughput')

            axis_client_throughput.set_xlabel('Time (seconds)')
            axis_client_throughput.set_ylabel('Throughput (Mbps)')
            axis_client_throughput.set_title(f'Client Throughput for {phase_code} with {algorithm_variant.upper()}')
            axis_client_throughput.legend()
            axis_client_throughput.grid(True)

            output_client_graph = os.path.join(results_location, f'{phase_code}_{algorithm_variant}_client_comparison.png')
            figure_client_throughput.savefig(output_client_graph)
            plt.close(figure_client_throughput)
            print(f"Client throughput graph for {phase_code} with {algorithm_variant} saved to '{output_client_graph}'.")

    summary_data_bandwidth = []
    for phase_id, clients_in_phase in experiment_phases.items():
        for algorithm_option in algorithm_choices:
            for client_name in clients_in_phase:
                json_data_file = os.path.join(results_location, f'{client_name}_{phase_id}_{algorithm_option}.json')
                if os.path.isfile(json_data_file):
                    data_metrics = retrieve_throughput_data(json_data_file)
                    if data_metrics:
                        summary_data_bandwidth.append({
                            'Configuration': phase_id,
                            'Algorithm': algorithm_option,
                            'Client': client_name,
                            'Goodput (Mbps)': f"{data_metrics['achieved_goodput']:.2f}",
                            'Retransmits': data_metrics['resend_count'],
                            'Packet Loss (%)': f"{data_metrics['packet_drop_ratio']:.2f}"
                        })

    if summary_data_bandwidth:
        summary_bandwidth_file = os.path.join(results_location, 'bandwidth_summary.txt')
        with open(summary_bandwidth_file, 'w') as summary_output_file:
            summary_output_file.write("Custom Bandwidth Experiment Summary:\n")
            summary_output_file.write("-" * 100 + "\n")
            summary_output_file.write(f"{'Configuration':<15} {'Algorithm':<10} {'Client':<6} {'Goodput (Mbps)':<15} {'Retransmits':<12} {'Packet Loss (%)':<15}\n")
            summary_output_file.write("-" * 100 + "\n")

            for row_details in summary_data_bandwidth:
                summary_output_file.write(f"{row_details['Configuration']:<15} {row_details['Algorithm']:<10} {row_details['Client']:<6} {row_details['Goodput (Mbps)']:<15} {row_details['Retransmits']:<12} {row_details['Packet Loss (%)']:<15}\n")
                print(f"{row_details['Configuration']:<15} {row_details['Algorithm']:<10} {row_details['Client']:<6} {row_details['Goodput (Mbps)']:<15} {row_details['Retransmits']:<12} {row_details['Packet Loss (%)']:<15}")

            summary_output_file.write("-" * 100 + "\n")
        print(f"Bandwidth experiment summary saved to '{summary_bandwidth_file}'.")

def analyze_loss_impact_experiment(base_results_dir, algo_variants, packet_loss_percentage):
    """Analyzes and summarizes results from the packet loss experiment."""
    print(f"\nAnalyzing {packet_loss_percentage}% packet loss experiment in '{base_results_dir}'.")

    client_endpoints = ['h1', 'h3', 'h4']

    figure_throughput_comparison, axis_throughput_comparison = plt.subplots(figsize=(12, 6))

    for algorithm_option in algo_variants:
        aggregated_throughputs = {}
        client_count_algo = 0

        for client_id in client_endpoints:
            json_file_path = os.path.join(base_results_dir, f'{client_id}_d_{packet_loss_percentage}_{algorithm_option}.json')
            if os.path.isfile(json_file_path):
                data_metrics = retrieve_throughput_data(json_file_path)
                if data_metrics and data_metrics['time_points'] and data_metrics['bandwidth_values']:
                    client_count_algo += 1
                    for time_index, throughput_value in zip(data_metrics['time_points'], data_metrics['bandwidth_values']):
                        aggregated_throughputs[time_index] = aggregated_throughputs.get(time_index, 0) + throughput_value

        if client_count_algo > 0:
            time_sequence = sorted(aggregated_throughputs.keys())
            average_throughput_values = [aggregated_throughputs[t] / client_count_algo for t in time_sequence]
            axis_throughput_comparison.plot(time_sequence, average_throughput_values, label=f"{algorithm_option}")

    axis_throughput_comparison.set_xlabel('Time (seconds)')
    axis_throughput_comparison.set_ylabel('Average Throughput per Client (Mbps)')
    axis_throughput_comparison.set_title(f'Average Throughput with {packet_loss_percentage}% Packet Loss')
    axis_throughput_comparison.legend()
    axis_throughput_comparison.grid(True)

    output_throughput_figure = os.path.join(base_results_dir, f'throughput_comparison_{packet_loss_percentage}pct_loss.png')
    figure_throughput_comparison.savefig(output_throughput_figure)
    plt.close(figure_throughput_comparison)
    print(f"Throughput comparison graph for {packet_loss_percentage}% loss saved to '{output_throughput_figure}'.")

    retransmits_per_algorithm = {algo: 0 for algo in algo_variants}
    goodput_per_algorithm = {algo: 0 for algo in algo_variants}
    total_clients_per_algo = {algo: 0 for algo in algo_variants}

    for algorithm_option in algo_variants:
        for client_id in client_endpoints:
            json_file_path = os.path.join(base_results_dir, f'{client_id}_d_{packet_loss_percentage}_{algorithm_option}.json')
            if os.path.isfile(json_file_path):
                data_metrics = retrieve_throughput_data(json_file_path)
                if data_metrics:
                    retransmits_per_algorithm[algorithm_option] += data_metrics['resend_count']
                    goodput_per_algorithm[algorithm_option] += data_metrics['achieved_goodput']
                    total_clients_per_algo[algorithm_option] += 1

    figure_performance_comparison, axis_performance_comparison_1 = plt.subplots(figsize=(10, 6))

    x_axis_positions = np.arange(len(algo_variants))
    bar_segment_width = 0.35

    retransmit_data_points = [retransmits_per_algorithm[algo] / total_clients_per_algo[algo] if total_clients_per_algo[algo] > 0 else 0 for algo in algo_variants]
    bars_1 = axis_performance_comparison_1.bar(x_axis_positions - bar_segment_width/2, retransmit_data_points, bar_segment_width, label='Avg Retransmissions')
    axis_performance_comparison_1.set_xlabel('Congestion Control Algorithm')
    axis_performance_comparison_1.set_ylabel('Average Retransmissions per Client')

    axis_performance_comparison_2 = axis_performance_comparison_1.twinx()
    goodput_data_points = [goodput_per_algorithm[algo] / total_clients_per_algo[algo] if total_clients_per_algo[algo] > 0 else 0 for algo in algo_variants]
    bars_2 = axis_performance_comparison_2.bar(x_axis_positions + bar_segment_width/2, goodput_data_points, bar_segment_width, label='Avg Goodput', color='orange')
    axis_performance_comparison_2.set_ylabel('Average Goodput per Client (Mbps)')

    axis_performance_comparison_1.set_title(f'Performance Under {packet_loss_percentage}% Packet Loss')
    axis_performance_comparison_1.set_xticks(x_axis_positions)
    axis_performance_comparison_1.set_xticklabels(algo_variants)

    lines_1, labels_1 = axis_performance_comparison_1.get_legend_handles_labels()
    lines_2, labels_2 = axis_performance_comparison_2.get_legend_handles_labels()
    axis_performance_comparison_1.legend(lines_1 + lines_2, labels_1 + labels_2, loc='upper left')

    plt.tight_layout()
    output_performance_figure = os.path.join(base_results_dir, f'performance_comparison_{packet_loss_percentage}pct_loss.png')
    figure_performance_comparison.savefig(output_performance_figure)
    plt.close(figure_performance_comparison)
    print(f"Performance comparison graph for {packet_loss_percentage}% loss saved to '{output_performance_figure}'.")

    summary_data_loss = []
    for algorithm_option in algo_variants:
        for client_id in client_endpoints:
            json_file_path = os.path.join(base_results_dir, f'{client_id}_d_{packet_loss_percentage}_{algorithm_option}.json')
            if os.path.isfile(json_file_path):
                data_metrics = retrieve_throughput_data(json_file_path)
                if data_metrics:
                    summary_data_loss.append({
                        'Algorithm': algorithm_option,
                        'Client': client_id,
                        'Goodput (Mbps)': f"{data_metrics['achieved_goodput']:.2f}",
                        'Retransmits': data_metrics['resend_count'],
                        'Packet Loss (%)': f"{data_metrics['packet_drop_ratio']:.2f}"
                    })

    if summary_data_loss:
        summary_loss_file = os.path.join(base_results_dir, f'loss_{packet_loss_percentage}pct_summary.txt')
        with open(summary_loss_file, 'w') as summary_output_stream:
            summary_output_stream.write(f"{packet_loss_percentage}% Packet Loss Experiment Summary:\n")
            summary_output_stream.write("-" * 80 + "\n")
            summary_output_stream.write(f"{'Algorithm':<10} {'Client':<6} {'Goodput (Mbps)':<15} {'Retransmits':<12} {'Packet Loss (%)':<15}\n")
            summary_output_stream.write("-" * 80 + "\n")

            for record_item in summary_data_loss:
                summary_output_stream.write(f"{record_item['Algorithm']:<10} {record_item['Client']:<6} {record_item['Goodput (Mbps)']:<15} {record_item['Retransmits']:<12} {record_item['Packet Loss (%)']:<15}\n")
                print(f"{record_item['Algorithm']:<10} {record_item['Client']:<6} {record_item['Goodput (Mbps)']:<15} {record_item['Retransmits']:<12} {record_item['Packet Loss (%)']:<15}")

            summary_output_stream.write("-" * 80 + "\n")
        print(f"Summary for {packet_loss_percentage}% loss experiment saved to '{summary_loss_file}'.")

def main():
    argument_parser = argparse.ArgumentParser(description='Analyze TCP congestion control experiment outcomes')
    argument_parser.add_argument('--experiment', choices=['a', 'b', 'c', 'd1', 'd5', 'all'], default='all',
                                 help='Select experiment for analysis (a, b, c, d1, d5, or all)')

    parsed_arguments = argument_parser.parse_args()
    selected_experiment = parsed_arguments.experiment

    congestion_algorithms = ['reno', 'bic', 'highspeed']

    if selected_experiment in ['a', 'all']:
        generate_throughput_graph('results/experiment_a', congestion_algorithms)
        generate_window_size_graph('results/experiment_a', congestion_algorithms)
        generate_summary_report('results/experiment_a', congestion_algorithms)
    
    if selected_experiment in ['b', 'all']:
        analyze_staggered_start_experiment('results/experiment_b', congestion_algorithms)

    if selected_experiment in ['c', 'all']:
        analyze_bandwidth_variation_experiment('results/experiment_c', congestion_algorithms)

    if selected_experiment in ['d1', 'all']:
        analyze_loss_impact_experiment('results/experiment_d_1', congestion_algorithms, 1)

    if selected_experiment in ['d5', 'all']:
        analyze_loss_impact_experiment('results/experiment_d_5', congestion_algorithms, 5)

    print("Experiment analysis completed!")

if __name__ == '__main__':
    main()