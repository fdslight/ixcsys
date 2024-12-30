

using System.Net;
using System.Net.Sockets;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading;

namespace MyProject{

    class TapIO{
        String TapDevName;
        String NicName;
        int TapFd=-1;

        Program MainWorker;
        byte[] RecvBuffer;

        public TapIO(Program m,String devname,String nicName){
            MainWorker=m;
            TapDevName=devname;
            NicName=nicName;

            RecvBuffer=new byte[4096];

            TapFd=Create(devname);

            if(TapFd<2){
                // 抛出异常
                System.Console.WriteLine("ERROR:cannot create tap device");
                System.Environment.Exit(-1);
            }
            Up(devname);
            
            MainWorker.TapDevOk=true;
            //System.Console.WriteLine(TapFd);
            CreateBridgeNet();

        }

        public void StopWork(){
            DeleteBridgeNet();
            Close(TapFd);
        }

        protected void ReadAndSendToTunnel(){
            if(!MainWorker.UdpTunnelOk) return;

            unsafe{
                fixed(byte *p=&RecvBuffer[20]){
                    Int64 rs=_Read(TapFd,p,4076);
                    if(rs<14) return;
                    MainWorker.Tunnel.SendData(RecvBuffer,(int)rs);
                }
            }
            
        }

        public void WriteData(byte[] buffer,int size){
            unsafe{
                fixed(byte *p=&buffer[20]){
                Int64 wsize=_Write(TapFd,p,(UInt64)size);
                    if(wsize < 1){
                        //System.Console.WriteLine("ERROR:cannot write to tap device");
                        return;
                    }
                }
            }
        }

        public void ioloop(){
            for(;;){
                ReadAndSendToTunnel();
            }
        }

        private void CreateBridgeNet(){
            int rs=0;
            rs=_system("ip link add name ixcpassbr type bridge");
            rs=_system("ip link set dev ixcpassbr up");
            rs=_system($"ip link set {NicName} promisc on");
            rs=_system($"ip link set {TapDevName} promisc on");
            rs=_system($"ip link set dev {NicName} master ixcpassbr");
            rs=_system($"ip link set dev {TapDevName} master ixcpassbr");
            
            rs=_system("echo 1 > /proc/sys/net/ipv6/conf/ixcpassbr/disable_ipv6");
            rs=_system($"echo 1 > /proc/sys/net/ipv6/conf/{TapDevName}/disable_ipv6");
            rs=_system($"echo 1 > /proc/sys/net/ipv6/conf/{NicName}/disable_ipv6");
        }

        private void DeleteBridgeNet(){
            int rs=0;
            rs=_system($"ip link set {TapDevName} nomaster");
            rs=_system($"ip link set {NicName} nomaster");
            rs=_system($"ip link del ixcpassbr");         
        }

        [DllImport("liblinux_tap.so",EntryPoint ="tap_create")]
        static extern int Create(String devname);

        [DllImport("liblinux_tap.so",EntryPoint ="tap_close")]
        static extern void Close(int fd);


        [DllImport("liblinux_tap.so",EntryPoint ="tap_up")]
        static extern int Up(String devname);

        [DllImport("liblinux_tap.so",EntryPoint ="tap_read")]
        static extern unsafe Int64 _Read(int fd,byte* buffer,System.UInt64 count);

        [DllImport("liblinux_tap.so",EntryPoint ="tap_write")]
        static extern unsafe Int64 _Write(int fd,byte* buffer,System.UInt64 count);

        [DllImport("libc.so.6",EntryPoint ="system")]
        private static extern unsafe int _system(String cmd);
        
    }

    class UdpTunnel{
        private Socket TunnelSocket;
        IPAddress ? PeerAddress;
        private String Host;
        private bool IsNeedParseHost=false;
        Program MainWorker;
        byte[] Key;
        EndPoint RemoteIp;
        private long Uptime;
        public UdpTunnel(Program m,int port,string host,string Skey){
            RemoteIp = new IPEndPoint(IPAddress.Any, 0);
            MainWorker=m;
            Host=host;
            IPEndPoint LocalPoint=new IPEndPoint(0,port);
            TunnelSocket=new Socket(AddressFamily.InterNetwork,SocketType.Dgram,ProtocolType.Udp);    
            TunnelSocket.Bind(LocalPoint);

            MainWorker.UdpTunnelOk=true;
            Key=new byte[16];

            if(!IPAddress.TryParse(host,out PeerAddress)){
                IsNeedParseHost=true;
                PeerAddress=GetPeerAddress();
            }

            Uptime=DateTimeOffset.Now.ToUnixTimeSeconds();
            SetKey(Skey);
        }

        public void SendData(byte[] buf,int size){
            PeerAddress=GetPeerAddress();

            if(PeerAddress==null){
                return;
            }

            IntPtr x=_memcpy(buf,Key,16);
            buf[16]=2;
            buf[19]=6;
            // 这里需要加上头部的20个字节
            TunnelSocket.SendTo(buf,0,size+20,SocketFlags.None,new IPEndPoint(PeerAddress,8964));
        }


        public void SetKey(string Skey){
            using var md5 = System.Security.Cryptography.MD5.Create();
            byte[] inputBytes = System.Text.Encoding.ASCII.GetBytes(Skey);

            Key = md5.ComputeHash(inputBytes);

        }

        [DllImport("libc.so.6",EntryPoint ="memcmp")]	
        private static extern unsafe int _memcmp(byte[] b1, byte[] b2, int count);

        [DllImport("libc.so.6",EntryPoint ="memcpy")]
        private static extern unsafe IntPtr _memcpy(byte[] dst,byte[] src,int size);

        protected void RecvData(){
          
            byte[] buffer=new byte[4096];
            int size=TunnelSocket.ReceiveFrom(buffer,4096,SocketFlags.None,ref RemoteIp);
            IPEndPoint IpInfo=(IPEndPoint)RemoteIp;

            if(size<16) return;
            if(IpInfo.Port!=8964) return;

            // key不一致丢弃数据包
            if(_memcmp(buffer,Key,16)!=0){
                //System.Console.WriteLine("drop data");
                return;
            }

            MainWorker.Tap.WriteData(buffer,size);
        }

        public int GetBindPort(){
            IPEndPoint? local =TunnelSocket.LocalEndPoint as IPEndPoint;

            if(local!=null){
                return local.Port;
            }
            return -1;
        }

        private IPAddress? GetPeerAddress(){
            if(!IsNeedParseHost){
                return PeerAddress;
            }
            
            long nowtime=DateTimeOffset.Now.ToUnixTimeSeconds();

            
            // 60秒更新一次主机名
            if(nowtime-Uptime < 60 && nowtime-Uptime>=0){
                return PeerAddress;
            }

            IPHostEntry entry;

            try{
                entry=Dns.GetHostEntry(Host,AddressFamily.InterNetwork);
            }catch(SocketException){
                System.Console.WriteLine($"ERROR:not found Host {Host} ip address");
                return null;
            }
            
            if(entry.AddressList.Length<1){
                return null;
            }

            PeerAddress=entry.AddressList[0];

            return PeerAddress;
        }

        public void ioloop(){
            for(;;){
                RecvData();
            }
        }

    }

    class Program{
        public UdpTunnel Tunnel;
        public TapIO Tap;
        public bool UdpTunnelOk=false;
        public bool TapDevOk=false;
        private static volatile bool _s_stop = false;
        private static Program ? My;

        protected void CreateTunnelWorker(){
            ThreadStart s=new ThreadStart(Tunnel.ioloop);
            Thread task=new Thread(s);

            task.IsBackground=true;
            task.Start();

            //task.Join();
        }

        protected void CreateTapWorker(){
            ThreadStart s=new ThreadStart(Tap.ioloop);
            Thread task=new Thread(s);

            task.IsBackground=true;
            task.Start();

            //task.Join();
        }

        public Program(string nic,int port,string host,string Skey){
            Tunnel=new UdpTunnel(this,port,host,Skey);
            Tap=new TapIO(this,"ixcpass",nic);
        }

        protected static void Console_CancelKeyPress(object? sender, ConsoleCancelEventArgs e){
            e.Cancel = true;
            _s_stop = true;

            if(My==null) return;

            My.UdpTunnelOk=false;
            My.TapDevOk=false;

            //Thread.Sleep(10000);

            My.Tap.StopWork();

            System.Console.WriteLine("stop process");
        }

        static void Main(String[] args){
            String helper="helper:LocalNicName LocalPort RemoteHost Key";
            int port;

            if(args.Length!=4){
                System.Console.WriteLine(helper);
                return;
            }

            try{
                port=Int32.Parse(args[1]);
            }catch(FormatException){
                System.Console.WriteLine($"ERROR:wrong LocalPort value {args[0]}");
                return;
            }

            if(port<1  || port >= 0xffff){
                System.Console.WriteLine($"ERROR:wrong LocalPort value {args[0]}");
                return;
            }

            My=new Program(args[0],port,args[2],args[3]);

            My.CreateTapWorker();
            My.CreateTunnelWorker();

            Console.CancelKeyPress += new ConsoleCancelEventHandler(Console_CancelKeyPress);
            while (!_s_stop){
                Thread.Sleep(3000);
            }   
        }
    }

}