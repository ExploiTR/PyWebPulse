import dns.resolver
import time
import logging
import platform
import subprocess # For getting system DNS on Windows/Linux

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# List of standard public DNS servers to test against
STANDARD_DNS_SERVERS = {
    "Google": "8.8.8.8",
    "Cloudflare": "1.1.1.1",
    "Quad9": "9.9.9.9",
    "OpenDNS": "208.67.222.222",
    "AdGuard DNS": "94.140.14.14",
    "Comodo Secure DNS": "8.26.56.26",
}

# Domain to use for latency test (should be common, unlikely to be cached locally)
TEST_DOMAIN = "www.google.com" # Or another high-availability domain

def get_system_dns_servers():
    """Tries to get the system's configured DNS servers."""
    servers = []
    system = platform.system()
    try:
        if system == "Windows":
            # Execute ipconfig /all and parse output
            cmd = "ipconfig /all"
            proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, text=True)
            output, _ = proc.communicate()
            in_dns_section = False
            for line in output.splitlines():
                line = line.strip()
                if "DNS Servers" in line:
                    in_dns_section = True
                    parts = line.split(':')
                    if len(parts) > 1 and parts[1].strip():
                         servers.append(parts[1].strip())
                elif in_dns_section and line.startswith(" ") and ":" not in line and line:
                    servers.append(line)
                elif line == "": # Blank line often separates sections
                    in_dns_section = False

        elif system == "Linux" or system == "Darwin": # Linux or macOS
            # Parse /etc/resolv.conf
            with open("/etc/resolv.conf", "r") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("nameserver"):
                        parts = line.split()
                        if len(parts) > 1:
                            servers.append(parts[1])
    except Exception as e:
        logging.warning(f"Could not automatically detect system DNS servers: {e}")

    # Return unique, valid-looking IPs (simple check)
    valid_servers = [s for s in set(servers) if '.' in s or ':' in s] # Basic IP format check
    logging.info(f"Detected system DNS servers: {valid_servers}")
    return valid_servers if valid_servers else ['OS Default (Not Detected)'] # Fallback label

def measure_dns_latency(domain, dns_server, timeout=2):
    """Measures latency for a single DNS query."""
    resolver = dns.resolver.Resolver()
    resolver.nameservers = [dns_server]
    resolver.timeout = timeout
    resolver.lifetime = timeout

    start_time = time.perf_counter()
    try:
        # Perform a simple A record query
        resolver.resolve(domain, 'A', raise_on_no_answer=False) # Don't error if no A record specifically
        end_time = time.perf_counter()
        latency_ms = (end_time - start_time) * 1000
        return round(latency_ms, 2), "Success"
    except dns.exception.Timeout:
        return -1, f"Timeout ({timeout}s)"
    except dns.resolver.NoNameservers as e:
         return -1, f"No Nameservers ({e})"
    except Exception as e:
        logging.warning(f"DNS query failed for {domain} @{dns_server}: {e}")
        return -1, f"Error ({type(e).__name__})"


def run_dns_benchmark():
    """Runs latency tests against system and standard DNS servers."""
    results = {}

    # Test System DNS
    system_servers = get_system_dns_servers()
    if system_servers and system_servers[0] != 'OS Default (Not Detected)':
         # Test only the first detected system server for simplicity, or loop through all
         server_ip = system_servers[0]
         latency, status = measure_dns_latency(TEST_DOMAIN, server_ip)
         results[f"System ({server_ip})"] = {"latency_ms": latency, "status": status}
    else:
         results["System Default"] = {"latency_ms": -1, "status": "Not Detected"}


    # Test Standard DNS Servers
    for name, ip in STANDARD_DNS_SERVERS.items():
         latency, status = measure_dns_latency(TEST_DOMAIN, ip)
         results[f"{name} ({ip})"] = {"latency_ms": latency, "status": status}

    logging.info(f"DNS Benchmark Results: {results}")
    return results

# Example usage (for testing this file directly)
if __name__ == "__main__":
    benchmark_results = run_dns_benchmark()
    print("DNS Benchmark Results:")
    for server, result in benchmark_results.items():
        if result['status'] == 'Success':
            print(f"- {server}: {result['latency_ms']:.2f} ms")
        else:
            print(f"- {server}: {result['status']}")