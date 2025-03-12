from mininet.topo import Topo
from mininet.net import Mininet
from mininet.link import TCLink
from mininet.node import OVSController

class MyTopo(Topo):
    def build(self, **_opts):
        # Add switches
        s1 = self.addSwitch('s1')
        s2 = self.addSwitch('s2')
        s3 = self.addSwitch('s3')
        s4 = self.addSwitch('s4')
        
        # Add hosts
        h1 = self.addHost('h1')
        h2 = self.addHost('h2')
        h3 = self.addHost('h3')
        h4 = self.addHost('h4')
        h5 = self.addHost('h5')
        h6 = self.addHost('h6')
        h7 = self.addHost('h7')
        
        # Add links
        self.addLink(h1, s1)
        self.addLink(h2, s1)
        self.addLink(h3, s2)
        self.addLink(h4, s3)
        self.addLink(h5, s3)
        self.addLink(h6, s4)
        self.addLink(h7, s4)
        
        # Add switch-to-switch links 
        self.addLink(s1, s2)
        self.addLink(s2, s3)
        self.addLink(s3, s4)

def configure_network(bw1=10, bw2=10, bw3=10, loss=0):
    topo = MyTopo()
    net = Mininet(topo=topo, controller=OVSController, link=TCLink)
    s1, s2, s3, s4 = net.get('s1', 's2', 's3', 's4')
    links = [(s1, s2, bw1), (s2, s3, bw2, loss), (s3, s4, bw3)]
    for sA, sB, bw, *loss in links:
        link = net.linksBetween(sA, sB)[0]
        for intf in [link.intf1, link.intf2]:
            intf.config(bw=bw, r2q=100, loss=loss[0] if loss else 0)
    return net
