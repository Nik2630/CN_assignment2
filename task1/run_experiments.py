import os
import time
import subprocess
import argparse
from mininet.net import Mininet
from mininet.cli import CLI
from mininet.log import setLogLevel, info
from topo import configure_network

CC_ALGOS = ['reno', 'bic', 'highspeed']

def initiate_capture(net, node, file):
    os.makedirs(os.path.dirname(file), exist_ok=True)
    node.cmd(f'tcpdump -i {node.defaultIntf().name} -w {file} tcp &')
    return node.lastPid

def terminate_capture(node, pid):
    node.cmd(f'kill -9 {pid}')
    time.sleep(1)

def start_iperf_server(node, port=5201):
    node.cmd(f'iperf3 -s -p {port} -D')
    info(f'*** Server started on {node.name} port {port}\n')
    time.sleep(1)

def start_iperf_client(node, ip, port=5201, bw='10M', parallel=10, duration=150, cc='cubic'):
    output = f'iperf3_{node.name}_to_h7_{cc}.json'
    node.cmd(f'iperf3 -c {ip} -p {port} -b {bw} -P {parallel} -t {duration} -C {cc} -J > {output}')
    return output

def run_exp_a(net):
    info('*** Running Experiment A\n')
    h1, h7 = net.get('h1', 'h7')
    ip = h7.IP()
    for algo in CC_ALGOS:
        info(f'*** Starting experiment with {algo}\n')
        os.makedirs('results/experiment_a', exist_ok=True)
        pcap = f'results/experiment_a/h1_h7_{algo}.pcap'
        pid = initiate_capture(net, h7, pcap)
        start_iperf_server(h7)
        output = start_iperf_client(h1, ip, cc=algo)
        terminate_capture(h7, pid)
        os.system(f'mv {output} results/experiment_a/')
        h7.cmd('pkill -9 iperf3')
        time.sleep(2)

def run_exp_b(net):
    info('*** Running Experiment B\n')
    h1, h3, h4, h7 = net.get('h1', 'h3', 'h4', 'h7')
    ip = h7.IP()
    for algo in CC_ALGOS:
        info(f'*** Starting experiment with {algo}\n')
        os.makedirs('results/experiment_b', exist_ok=True)
        pcap = f'results/experiment_b/staggered_{algo}.pcap'
        pid = initiate_capture(net, h7, pcap)
        start_iperf_server(h7)
        h1.cmd(f'iperf3 -c {ip} -p 5201 -b 10M -P 10 -t 150 -C {algo} -J > results/experiment_b/h1_staggered_{algo}.json &')
        time.sleep(15)
        h3.cmd(f'iperf3 -c {ip} -p 5201 -b 10M -P 10 -t 120 -C {algo} -J > results/experiment_b/h3_staggered_{algo}.json &')
        time.sleep(15)
        h4.cmd(f'iperf3 -c {ip} -p 5201 -b 10M -P 10 -t 90 -C {algo} -J > results/experiment_b/h4_staggered_{algo}.json &')
        time.sleep(120)
        terminate_capture(h7, pid)
        h7.cmd('pkill -9 iperf3')
        time.sleep(2)

def run_exp_c(net):
    info('*** Running Experiment C\n')
    h1, h2, h3, h4, h7 = net.get('h1', 'h2', 'h3', 'h4', 'h7')
    ip = h7.IP()
    os.makedirs('results/experiment_c', exist_ok=True)
    for algo in CC_ALGOS:
        info(f'*** Starting experiment C with {algo}\n')
        pcap = f'results/experiment_c/c1_{algo}.pcap'
        pid = initiate_capture(net, h7, pcap)
        start_iperf_server(h7)
        start_iperf_client(h3, ip, cc=algo)
        terminate_capture(h7, pid)
        h7.cmd('pkill -9 iperf3')
        time.sleep(2)
        
        pcap = f'results/experiment_c/c2a_{algo}.pcap'
        pid = initiate_capture(net, h7, pcap)
        start_iperf_server(h7)
        h1.cmd(f'iperf3 -c {ip} -p 5201 -b 10M -P 10 -t 150 -C {algo} -J > results/experiment_c/h1_c2a_{algo}.json &')
        h2.cmd(f'iperf3 -c {ip} -p 5201 -b 10M -P 10 -t 150 -C {algo} -J > results/experiment_c/h2_c2a_{algo}.json &')
        time.sleep(150)
        terminate_capture(h7, pid)
        h7.cmd('pkill -9 iperf3')
        time.sleep(2)
        
        pcap = f'results/experiment_c/c2b_{algo}.pcap'
        pid = initiate_capture(net, h7, pcap)
        start_iperf_server(h7)
        h1.cmd(f'iperf3 -c {ip} -p 5201 -b 10M -P 10 -t 150 -C {algo} -J > results/experiment_c/h1_c2b_{algo}.json &')
        h3.cmd(f'iperf3 -c {ip} -p 5201 -b 10M -P 10 -t 150 -C {algo} -J > results/experiment_c/h3_c2b_{algo}.json &')
        time.sleep(150)
        terminate_capture(h7, pid)
        h7.cmd('pkill -9 iperf3')
        time.sleep(2)
        
        pcap = f'results/experiment_c/c2c_{algo}.pcap'
        pid = initiate_capture(net, h7, pcap)
        start_iperf_server(h7)
        h1.cmd(f'iperf3 -c {ip} -p 5201 -b 10M -P 10 -t 150 -C {algo} -J > results/experiment_c/h1_c2c_{algo}.json &')
        h3.cmd(f'iperf3 -c {ip} -p 5201 -b 10M -P 10 -t 150 -C {algo} -J > results/experiment_c/h3_c2c_{algo}.json &')
        h4.cmd(f'iperf3 -c {ip} -p 5201 -b 10M -P 10 -t 150 -C {algo} -J > results/experiment_c/h4_c2c_{algo}.json &')
        time.sleep(150)
        terminate_capture(h7, pid)
        h7.cmd('pkill -9 iperf3')
        time.sleep(2)

def run_exp_d(net, loss):
    info(f'*** Running Experiment D with {loss}% packet loss\n')
    h1, h3, h4, h7 = net.get('h1', 'h3', 'h4', 'h7')
    ip = h7.IP()
    os.makedirs(f'results/experiment_d_{loss}', exist_ok=True)
    for algo in CC_ALGOS:
        info(f'*** Starting experiment D with {algo} and {loss}% loss\n')
        pcap = f'results/experiment_d_{loss}/d_{loss}_{algo}.pcap'
        pid = initiate_capture(net, h7, pcap)
        start_iperf_server(h7)
        h1.cmd(f'iperf3 -c {ip} -p 5201 -b 10M -P 10 -t 150 -C {algo} -J > results/experiment_d_{loss}/h1_d_{loss}_{algo}.json &')
        h3.cmd(f'iperf3 -c {ip} -p 5201 -b 10M -P 10 -t 150 -C {algo} -J > results/experiment_d_{loss}/h3_d_{loss}_{algo}.json &')
        h4.cmd(f'iperf3 -c {ip} -p 5201 -b 10M -P 10 -t 150 -C {algo} -J > results/experiment_d_{loss}/h4_d_{loss}_{algo}.json &')
        time.sleep(150)
        terminate_capture(h7, pid)
        h7.cmd('pkill -9 iperf3')
        time.sleep(2)

def main():
    parser = argparse.ArgumentParser(description='Run TCP congestion control experiments')
    parser.add_argument('--option', choices=['a', 'b', 'c', 'd', 'all'], default='all', help='Experiment option to run (a, b, c, d, or all)')
    args = parser.parse_args()
    opt = args.option
    os.makedirs('results', exist_ok=True)
    setLogLevel('info')
    
    if opt in ['a', 'b', 'all']:
        net = configure_network()
        net.start()
        if opt in ['a', 'all']:
            run_exp_a(net)
        if opt in ['b', 'all']:
            run_exp_b(net)
        net.stop()
    
    if opt in ['c', 'all']:
        net = configure_network(bandwidth_s1_s2=100, bandwidth_s2_s3=50, bandwidth_s3_s4=100)
        net.start()
        run_exp_c(net)
        net.stop()
    
    if opt in ['d', 'all']:
        net = configure_network(bandwidth_s1_s2=100, bandwidth_s2_s3=50, bandwidth_s3_s4=100, loss_s2_s3=1)
        net.start()
        run_exp_d(net, 1)
        net.stop()
        
        net = configure_network(bandwidth_s1_s2=100, bandwidth_s2_s3=50, bandwidth_s3_s4=100, loss_s2_s3=5)
        net.start()
        run_exp_d(net, 5)
        net.stop()
    
    info('*** All experiments completed\n')

if __name__ == '__main__':
    main()