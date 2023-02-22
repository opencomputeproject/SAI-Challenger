import json
import paramiko
import redis
import time
import warnings
from cryptography.utils import CryptographyDeprecationWarning
warnings.filterwarnings("ignore", category=CryptographyDeprecationWarning)


class SaiDut:
    def __init__(self, cfg):
        self.alias = cfg.get("alias", "default")
        self.server_ip = cfg["ip"]
        self.username = cfg.get("username", "admin")
        self.password = cfg.get("password", "admin")
        self.ssh = None

    def cleanup(self):
        raise NotImplementedError

    def init(self):
        raise NotImplementedError

    def deinit(self):
        raise NotImplementedError

    def _connect(self):
        if self.ssh:
            return
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect(self.server_ip, username=self.username, password=self.password)

    def service_is_active(self, service):
        self._connect()
        _, stdout, _ = self.ssh.exec_command(f"systemctl is-active {service}")
        output = stdout.read().decode("utf-8")
        return "inactive" not in output

    def container_is_running(self, container):
        self._connect()
        _, stdout, _ = self.ssh.exec_command(f"docker inspect {container}")
        output = stdout.read().decode("utf-8")
        return json.loads(output)[0]["State"]["Running"]

    def assert_container_state(self, container, is_running=True, tout=30):
        for i in range(tout):
            if self.container_is_running(container) == is_running:
                return
            if i + 1 < tout:
                time.sleep(1)
        state = "not running" if is_running else "running"
        assert False, f"The {container} container is still not running after {tout} seconds..."

    def assert_service_state(self, service, is_active=True, tout=30):
        for i in range(tout):
            if self.service_is_active(service) == is_active:
                return
            if i + 1 < tout:
                time.sleep(1)
        state = "inactive" if is_active else "active"
        assert False, f"The {service} service is still {state} after {tout} seconds..."

    @staticmethod
    def spawn(cfg) -> 'SaiDut':
        sai_dut = None
        if cfg.get("mode", None) == "sonic":
            sai_dut = SaiDutSonic(cfg)
        return sai_dut


class SaiDutSonic(SaiDut):
    def __init__(self, cfg):
        super().__init__(cfg)
        self.port = cfg["port"]
        self.username = cfg.get("username", "admin")
        self.password = cfg.get("password", "YourPaSsWoRd")
        self.ssh = None

    def init(self):
        # Make SSH connection to SONiC device
        self._connect()

        # In SONiC environment, Redis is listening on loopback interface only.
        # So, we can retrieve device metadata though SSH only.
        # Try to get metadata from a file first.
        _, stdout, _ = self.ssh.exec_command('cat device_metadata.log')
        output = stdout.readlines()
        if len(output) <= 1:
            assert self.container_is_running("database")

            # Try to get metadata from CONFIG_DB
            _, stdout, _ = self.ssh.exec_command('redis-cli -n 4 --raw hgetall "DEVICE_METADATA|localhost"')
            output = stdout.readlines()
            assert len(output) > 1, "DEVICE_METADATA is not defines"

            # Write metadata to the file
            metadata = ""
            for line in output:
                metadata += line
            metadata = metadata[:-1]
            self.ssh.exec_command(f"echo \"{metadata}\" > device_metadata.log")

        device_metadata = {}
        for i in range(0, len(output), 2):
            device_metadata[output[i][:-1]] = output[i + 1][:-1]

        if self.container_is_running("database"):
            # Enable Redis server to listen on all interfaces
            cmd = "echo \"sed -ri 's/--bind.*--port/--bind 0.0.0.0 --port/' /usr/share/sonic/templates/supervisord.conf.j2\" > redis_bind_fix.sh"
            self.ssh.exec_command(cmd)
            self.ssh.exec_command("docker cp redis_bind_fix.sh database:/")
            self.ssh.exec_command("docker exec database bash redis_bind_fix.sh")

            # Stop all SONiC services
            for service in ["monit", "pmon", "sonic.target", "database"]:
                self.ssh.exec_command(f"sudo systemctl stop {service}")
                self.ssh.exec_command(f"sudo systemctl mask {service}")
                self.assert_service_state(service, is_active=False, tout=60)

            # Stop SyncD just in case it's the second run of SAI-C
            self.ssh.exec_command("docker stop syncd")
            self.assert_container_state("syncd", is_running=False)

        # Apply Redis config change
        if self.container_is_running("database"):
            self.ssh.exec_command("docker stop database")
            self.assert_container_state("database", is_running=False)
        self.ssh.exec_command("docker start database")
        self.assert_container_state("database", is_running=True)
        self._assert_redis_is_available()

        # Flush SONiC Redis content
        r = redis.Redis(host=self.server_ip, port=self.port, db=1)
        r.flushall()

        # Write to CONFIG_DB SONiC device information needed on syncd start
        config_db = redis.Redis(host=self.server_ip, port=self.port, db=4)
        config_db.hmset("DEVICE_METADATA|localhost", device_metadata)
        config_db.set("CONFIG_DB_INITIALIZED", "1")

    def deinit(self):
        # Make SSH connection to SONiC device
        self._connect()

        # Enable all SONiC services in the reverse order
        for service in reverse(["monit", "pmon", "sonic.target", "database"]):
            if self.service_is_active(service):
                continue
            self.ssh.exec_command(f"sudo systemctl unmask {service}")
            self.ssh.exec_command(f"sudo systemctl restart {service}")

    def cleanup(self):
        self._connect()
        self.ssh.exec_command("docker stop syncd")
        self.assert_container_state("syncd", is_running=False)
        # Flush ASIC_DB content
        r = redis.Redis(host=self.server_ip, port=self.port, db=1)
        r.flushdb()
        self.ssh.exec_command("docker start syncd")

    def _assert_redis_is_available(self, tout=30):
        start_time = time.time()
        r = redis.Redis(host=self.server_ip, port=self.port, db=0)
        while True:
            try:
                r.ping()
                return
            except:
                if time.time() - start_time < tout:
                    time.sleep(1)
                    continue
            assert False, f"Redis server is still not available after {tout} seconds..."
