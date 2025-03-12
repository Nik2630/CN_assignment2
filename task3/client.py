import socket
import time
import argparse
import os

def generate_sample_file(path, size=4096):
    with open(path, 'wb') as out_file:
        out_file.write(os.urandom(size))
    return path

def set_client_options(sock, use_nagle, use_delayed_ack):
    if not use_nagle:
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    if not use_delayed_ack:
        try:
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_QUICKACK, 1)
        except AttributeError:
            print("TCP_QUICKACK not supported on this platform")

def transmit_data(server_addr, port_number, data_buffer, rate, duration, use_nagle, use_delayed_ack):
    client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    set_client_options(client_sock, use_nagle, use_delayed_ack)
    client_sock.connect((server_addr, port_number))
    
    print(f"Connected to {server_addr}:{port_number}")
    print(f"Nagle's algorithm is {'active' if use_nagle else 'inactive'}")
    print(f"Delayed ACK is {'active' if use_delayed_ack else 'inactive'}")
    print(f"Transfer scheduled at {rate} B/s for {duration} sec")
    
    total_bytes = 0
    packet_count = 0
    ack_count = 0
    lost_count = 0
    start = time.time()
    finish = start + duration
    chunk_size = 40
    sleep_interval = 1.0 / (rate / chunk_size)
    pos = 0
    
    try:
        while time.time() < finish:
            segment = data_buffer[pos: pos + chunk_size]
            if not segment:
                break
            client_sock.sendall(segment)
            packet_count += 1
            total_bytes += len(segment)
            pos = (pos + chunk_size) % len(data_buffer)
            
            try:
                client_sock.settimeout(1.0)
                response = client_sock.recv(3)
                if response == b'ACK':
                    ack_count += 1
            except socket.timeout:
                lost_count += 1
            
            time.sleep(sleep_interval)
    except Exception as err:
        print(f"Transmission issue: {err}")
    finally:
        elapsed = time.time() - start
        achieved_rate = total_bytes / elapsed if elapsed > 0 else 0
        effective_rate = (ack_count * chunk_size) / elapsed if elapsed > 0 else 0
        loss_ratio = lost_count / packet_count if packet_count > 0 else 0
        
        print("\nTransfer finished")
        print(f"Elapsed time: {elapsed:.2f} sec")
        print(f"Total bytes sent: {total_bytes}")
        print(f"Packets transmitted: {packet_count}")
        print(f"ACKs confirmed: {ack_count}")
        print(f"Achieved throughput: {achieved_rate:.2f} B/s")
        print(f"Effective goodput: {effective_rate:.2f} B/s")
        print(f"Packet loss: {loss_ratio:.2%}")
        
        client_sock.close()
        return {
            "throughput": achieved_rate,
            "goodput": effective_rate,
            "loss": loss_ratio,
            "bytes": total_bytes,
            "packets": packet_count,
            "acks": ack_count,
            "time": elapsed,
        }

def start_client(server_ip, port, file_path, rate, duration, use_nagle, use_delayed_ack):
    with open(file_path, 'rb') as file_handle:
        content = file_handle.read()
    return transmit_data(server_ip, port, content, rate, duration, use_nagle, use_delayed_ack)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TCP Client with adjustable settings")
    parser.add_argument('--server', type=str, default='127.0.0.1', help="IP address of the server")
    parser.add_argument('--port', type=int, default=5000, help="Target server port")
    parser.add_argument('--rate', type=int, default=40, help="Transmission rate in bytes per second")
    parser.add_argument('--duration', type=int, default=120, help="Time span for transmission in seconds")
    parser.add_argument('--nagle', type=int, default=1, help="Toggle Nagle's algorithm (1=enabled, 0=disabled)")
    parser.add_argument('--delayed-ack', type=int, default=1, help="Toggle Delayed ACK (1=enabled, 0=disabled)")
    
    config = parser.parse_args()
    sample_file = generate_sample_file('/tmp/test_file.bin')
    
    start_client(config.server, config.port, sample_file, config.rate, config.duration, bool(config.nagle), bool(config.delayed_ack))
