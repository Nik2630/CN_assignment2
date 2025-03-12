import os
import time
import json
from mininet.topo import Topo
from mininet.net import Mininet
from mininet.link import TCLink
from mininet.util import dumpNodeConnections
from mininet.log import setLogLevel

class DualHostTopology(Topo):
    def build(self):
        sw = self.addSwitch('s1')
        h_client = self.addHost('h1')
        h_server = self.addHost('h2')
        self.addLink(h_client, sw, bw=1, delay='5ms')
        self.addLink(h_server, sw, bw=1, delay='5ms')

def setup_environment():
    res_dir = "results"
    os.makedirs(res_dir, exist_ok=True)
    return res_dir

def create_sample_file(host):
    host.cmd('python3 -c "import os; open(\'/tmp/test_file.bin\', \'wb\').write(os.urandom(4096))"')

def run_single_config(cli_host, srv_host, conf, rate, dur):
    print(f"\nStarting test: {conf['name']}")
    print(f"Nagle set to {'ON' if conf['nagle'] else 'OFF'} & Delayed ACK set to {'ON' if conf['delayed_ack'] else 'OFF'}")
    
    srv_command = (
        'python3 server.py '
        f'--port 5000 --nagle {conf["nagle"]} --delayed-ack {conf["delayed_ack"]} '
        '> /tmp/server_output.txt 2>&1 &'
    )
    print(f"Launching server: {srv_command}")
    srv_host.cmd(srv_command)
    time.sleep(2)
    
    cli_command = (
        'python3 client.py '
        f'--server {srv_host.IP()} --port 5000 --rate {rate} --duration {dur} '
        f'--nagle {conf["nagle"]} --delayed-ack {conf["delayed_ack"]}'
    )
    print(f"Running client: {cli_command}")
    output = cli_host.cmd(cli_command)
    print(output)
    
    srv_host.cmd('pkill -f "python3 server.py"')
    time.sleep(2)
    return parse_output(output)

def parse_output(raw_output):
    metrics = {}
    for line in raw_output.strip().split('\n'):
        if "Throughput:" in line:
            try:
                metrics['throughput'] = float(line.split(':')[1].strip().split()[0])
            except Exception:
                metrics['throughput'] = 0.0
        elif "Goodput:" in line:
            try:
                metrics['goodput'] = float(line.split(':')[1].strip().split()[0])
            except Exception:
                metrics['goodput'] = 0.0
        elif "Packet loss rate:" in line:
            try:
                pl_val = line.split(':')[1].strip().rstrip('%')
                metrics['packet_loss_rate'] = float(pl_val) / 100
            except Exception:
                metrics['packet_loss_rate'] = 0.0
        elif "Bytes sent:" in line:
            try:
                metrics['bytes_sent'] = int(line.split(':')[1].strip())
            except Exception:
                metrics['bytes_sent'] = 0
        elif "Packets sent:" in line:
            try:
                pkt = int(line.split(':')[1].strip())
                metrics['packets_sent'] = pkt
                metrics['avg_packet_size'] = (metrics.get('bytes_sent', 0) / pkt) if pkt > 0 else 0.0
            except Exception:
                metrics['packets_sent'] = 0
                metrics['avg_packet_size'] = 0.0
    return metrics

def compile_report(result_data, res_dir):
    report_path = os.path.join(res_dir, "analysis.txt")
    with open(report_path, 'w') as report:
        report.write("=== TCP Metrics Analysis Report ===\n\n")
        report.write(f"{'Configuration':<25}{'Throughput (B/s)':<20}{'Goodput (B/s)':<20}"
                     f"{'Loss Rate':<20}{'Avg Packet Size (B)':<20}\n")
        report.write("-" * 85 + "\n")
        for cfg, stats in result_data.items():
            report.write(f"{cfg:<25}{stats.get('throughput',0):<20.2f}{stats.get('goodput',0):<20.2f}"
                         f"{stats.get('packet_loss_rate',0):<20.2%}{stats.get('avg_packet_size',0):<20.2f}\n")
        report.write("\nDetailed Observations:\n")
        # Compare Nagle on vs off
        nagle_on = {k: v for k, v in result_data.items() if 'nagle_on' in k}
        nagle_off = {k: v for k, v in result_data.items() if 'nagle_off' in k}
        
        avg_throughput_nagle_on = sum(v.get('throughput', 0) for v in nagle_on.values()) / len(nagle_on) if nagle_on else 0
        avg_throughput_nagle_off = sum(v.get('throughput', 0) for v in nagle_off.values()) / len(nagle_off) if nagle_off else 0
        
        report.write(f"1. Effect of Nagle's Algorithm:\n")
        report.write(f"   - Average throughput with Nagle on: {avg_throughput_nagle_on:.2f} B/s\n")
        report.write(f"   - Average throughput with Nagle off: {avg_throughput_nagle_off:.2f} B/s\n")
        report.write(f"   - Nagle's algorithm {'increases' if avg_throughput_nagle_on > avg_throughput_nagle_off else 'decreases'} throughput by {abs(avg_throughput_nagle_on - avg_throughput_nagle_off):.2f} B/s ({abs(avg_throughput_nagle_on - avg_throughput_nagle_off) / max(avg_throughput_nagle_off, 0.001):.2%})\n\n")
        
        # Compare DelACK on vs off
        delack_on = {k: v for k, v in result_data.items() if 'delack_on' in k}
        delack_off = {k: v for k, v in result_data.items() if 'delack_off' in k}
        
        avg_throughput_delack_on = sum(v.get('throughput', 0) for v in delack_on.values()) / len(delack_on) if delack_on else 0
        avg_throughput_delack_off = sum(v.get('throughput', 0) for v in delack_off.values()) / len(delack_off) if delack_off else 0
        
        report.write(f"2. Effect of Delayed ACK:\n")
        report.write(f"   - Average throughput with Delayed ACK on: {avg_throughput_delack_on:.2f} B/s\n")
        report.write(f"   - Average throughput with Delayed ACK off: {avg_throughput_delack_off:.2f} B/s\n")
        report.write(f"   - Delayed ACK {'increases' if avg_throughput_delack_on > avg_throughput_delack_off else 'decreases'} throughput by {abs(avg_throughput_delack_on - avg_throughput_delack_off):.2f} B/s ({abs(avg_throughput_delack_on - avg_throughput_delack_off) / max(avg_throughput_delack_off, 0.001):.2%})\n\n")
        
        # Find the best configuration
        best_config = max(result_data.items(), key=lambda x: x[1].get('goodput', 0))
        report.write(f"3. Best Configuration:\n")
        report.write(f"   - {best_config[0]} provides the highest goodput at {best_config[1].get('goodput', 0):.2f} B/s\n\n")
        
        # Theoretical explanation
        report.write("4. Explanation of Observations:\n")
        report.write("   - Nagle's Algorithm aims to reduce the number of small packets by buffering data until either a full-sized packet can be sent or an ACK is received.\n")
        report.write("   - Delayed ACK reduces the number of ACKs by delaying them, which can cause Nagle's algorithm to wait unnecessarily.\n")
        report.write("   - When both are enabled, they can create a 'lock-step' behavior where each is waiting for the other.\n")
        report.write("   - Disabling both typically gives the best interactive performance but may increase network overhead.\n\n")
        
        report.write("5. Recommendations:\n")
        report.write("   - For bulk transfers: Nagle on, Delayed ACK on - Reduces overhead, maximizes efficiency\n")
        report.write("   - For interactive applications: Nagle off, Delayed ACK off - Minimizes latency\n")
        report.write("   - For mixed workloads: Nagle off, Delayed ACK on - Good compromise\n")
        
    print(f"Report generated at {report_path}")

def execute_experiment():
    results_directory = setup_environment()
    topo = DualHostTopology()
    net = Mininet(topo=topo, link=TCLink)
    net.start()
    print("Current network links:")
    dumpNodeConnections(net.hosts)
    
    cli_host = net.get('h1')
    srv_host = net.get('h2')
    create_sample_file(cli_host)
    
    config_list = [
        {"nagle": 1, "delayed_ack": 1, "name": "nagle_on_delack_on"},
        {"nagle": 1, "delayed_ack": 0, "name": "nagle_on_delack_off"},
        {"nagle": 0, "delayed_ack": 1, "name": "nagle_off_delack_on"},
        {"nagle": 0, "delayed_ack": 0, "name": "nagle_off_delack_off"}
    ]
    test_rate = 40
    test_duration = 120
    compiled_results = {}
    
    for cfg in config_list:
        stats = run_single_config(cli_host, srv_host, cfg, test_rate, test_duration)
        compiled_results[cfg["name"]] = stats

    net.stop()
    with open(os.path.join(results_directory, "results.json"), 'w') as jf:
        json.dump(compiled_results, jf, indent=2)
    print(f"\nExperiment finished. Results saved to {results_directory}/results.json")
    compile_report(compiled_results, results_directory)

if __name__ == '__main__':
    setLogLevel('info')
    execute_experiment()
