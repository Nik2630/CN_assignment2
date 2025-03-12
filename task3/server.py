import socket
import time
import argparse

def adjust_socket_options(sock, use_nagle, use_delayed_ack):
    if not use_nagle:
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    if not use_delayed_ack:
        try:
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_QUICKACK, 1)
        except AttributeError:
            print("TCP_QUICKACK option not supported on this system")

def process_client(client_conn):
    total_data = 0
    packet_num = 0
    max_size = 0
    session_start = time.time()
    
    for packet in iter(lambda: client_conn.recv(4096), b''):
        packet_len = len(packet)
        total_data += packet_len
        packet_num += 1
        max_size = packet_len if packet_len > max_size else max_size
        client_conn.sendall(b'ACK')
    
    elapsed_time = time.time() - session_start
    data_rate = total_data / elapsed_time if elapsed_time > 0 else 0
    
    print("\nSession ended")
    print(f"Elapsed time: {elapsed_time:.2f} seconds")
    print(f"Total data received: {total_data} bytes")
    print(f"Packet count: {packet_num}")
    print(f"Data rate: {data_rate:.2f} bytes/sec")
    print(f"Largest packet: {max_size} bytes")

def launch_server(socket_port, use_nagle, use_delayed_ack):
    srv_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    adjust_socket_options(srv_socket, use_nagle, use_delayed_ack)
    
    srv_socket.bind(('0.0.0.0', socket_port))
    srv_socket.listen(1)
    
    print(f"Server started on port {socket_port}")
    print(f"Nagle is {'on' if use_nagle else 'off'}")
    print(f"Delayed ACK is {'on' if use_delayed_ack else 'off'}")
    
    client_sock, client_addr = srv_socket.accept()
    print(f"Incoming connection from {client_addr}")
    try:
        process_client(client_sock)
    except Exception as ex:
        print(f"An error occurred: {ex}")
    finally:
        client_sock.close()
        srv_socket.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TCP Server with flexible options")
    parser.add_argument('--port', type=int, default=5000, help="Port to host the server")
    parser.add_argument('--nagle', type=int, default=1, help="Activate Nagle's algorithm (1=on, 0=off)")
    parser.add_argument('--delayed-ack', type=int, default=1, help="Activate Delayed-ACK (1=on, 0=off)")
    
    cfg = parser.parse_args()
    launch_server(cfg.port, bool(cfg.nagle), bool(cfg.delayed_ack))
