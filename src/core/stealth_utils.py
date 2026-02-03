import random
import logging
from abc import ABC, abstractmethod
from typing import List, Optional, Dict

logger = logging.getLogger("GhostFetch.Stealth")

class ProxyStrategy(ABC):
    @abstractmethod
    def get_proxy(self, proxies: List[str]) -> Optional[str]:
        pass

class RoundRobinStrategy(ProxyStrategy):
    def __init__(self):
        self._index = 0

    def get_proxy(self, proxies: List[str]) -> Optional[str]:
        if not proxies:
            return None
        proxy = proxies[self._index % len(proxies)]
        self._index += 1
        return proxy

class RandomStrategy(ProxyStrategy):
    def get_proxy(self, proxies: List[str]) -> Optional[str]:
        if not proxies:
            return None
        return random.choice(proxies)

from urllib.parse import urlparse

class ProxyManager:
    """Manages proxy rotation, health tracking, and latency profiling."""
    def __init__(self, proxies: List[str], strategy: ProxyStrategy = RoundRobinStrategy()):
        self.proxies = [p for p in proxies if self._validate_proxy(p)]
        if len(self.proxies) < len(proxies):
            logger.warning(f"Removed {len(proxies) - len(self.proxies)} invalid proxies from the pool.")
        
        self.strategy = strategy
        self.bad_proxies = set()
        self.proxy_failures = {} # {proxy_url: count}
        self.proxy_latency = {}  # {proxy_url: [latency_ms, ...]}

    def _validate_proxy(self, proxy_url: str) -> bool:
        """Validate proxy URL format"""
        try:
            result = urlparse(proxy_url)
            return result.scheme in ['http', 'https'] and result.netloc
        except:
            return False

    def get_next_proxy(self) -> Optional[str]:
        # Filter out bad proxies
        available_proxies = [p for p in self.proxies if p not in self.bad_proxies]
        if not available_proxies:
            if self.proxies:
                logger.warning("All proxies marked as bad. Resetting proxy pool.")
                self.bad_proxies.clear()
                available_proxies = self.proxies
            else:
                return None
        
        # Performance Enhancement: Prefer low-latency proxies if using strategy that allows it
        # For now, we still rely on the strategy but could wrap it to sort by latency
        return self.strategy.get_proxy(available_proxies)

    def record_latency(self, proxy_url: str, latency_ms: float):
        if proxy_url not in self.proxy_latency:
            self.proxy_latency[proxy_url] = []
        self.proxy_latency[proxy_url].append(latency_ms)
        # Keep last 10 measurements
        if len(self.proxy_latency[proxy_url]) > 10:
            self.proxy_latency[proxy_url].pop(0)

    def mark_bad(self, proxy_url: str):
        if not proxy_url:
            return
        self.proxy_failures[proxy_url] = self.proxy_failures.get(proxy_url, 0) + 1
        if self.proxy_failures[proxy_url] >= 3:
            logger.error(f"Marking proxy as BAD: {proxy_url}")
            self.bad_proxies.add(proxy_url)

    def mark_good(self, proxy_url: str):
        if not proxy_url:
            return
        if proxy_url in self.proxy_failures:
            del self.proxy_failures[proxy_url]
        if proxy_url in self.bad_proxies:
            self.bad_proxies.remove(proxy_url)

class FingerprintGenerator:
    """Generates cohesive browser fingerprints to avoid detection."""
    
    PLATFORMS = [
        {
            "os": "Windows",
            "user_agents": [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            ],
            "screen_res": [{"width": 1920, "height": 1080}, {"width": 2560, "height": 1440}],
            "platform_name": "Win32"
        },
        {
            "os": "macOS",
            "user_agents": [
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
            ],
            "screen_res": [{"width": 1440, "height": 900}, {"width": 2880, "height": 1800}],
            "platform_name": "MacIntel"
        }
    ]

    LANGUAGES = ["en-US,en;q=0.9", "en-GB,en;q=0.8", "en-CA,en;q=0.8"]
    TIMEZONES = ["America/New_York", "Europe/London", "America/Los_Angeles", "Asia/Tokyo"]

    @classmethod
    def generate(cls) -> Dict:
        platform = random.choice(cls.PLATFORMS)
        ua = random.choice(platform["user_agents"])
        res = random.choice(platform["screen_res"])
        
        return {
            "user_agent": ua,
            "viewport": res,
            "screen": res,
            "locale": random.choice(["en-US", "en-GB"]),
            "timezone_id": random.choice(cls.TIMEZONES),
            "device_scale_factor": random.choice([1, 2]),
            "hardware_concurrency": random.choice([4, 8, 16]),
            "device_memory": random.choice([8, 16, 32]),
            "platform": platform["platform_name"]
        }

    @staticmethod
    def get_stealth_script(fingerprint: Dict) -> str:
        """Generates a JavaScript to be injected into the browser context."""
        return f"""
            // Basic overrides
            Object.defineProperty(navigator, 'webdriver', {{ get: () => undefined }});
            Object.defineProperty(navigator, 'languages', {{ get: () => ['{fingerprint['locale']}', 'en'] }});
            Object.defineProperty(navigator, 'platform', {{ get: () => '{fingerprint['platform']}' }});
            Object.defineProperty(navigator, 'hardwareConcurrency', {{ get: () => {fingerprint['hardware_concurrency']} }});
            Object.defineProperty(navigator, 'deviceMemory', {{ get: () => {fingerprint['device_memory']} }});
            
            // Canvas Fingerprint Protection (adds slight noise)
            const originalGetImageData = CanvasRenderingContext2D.prototype.getImageData;
            CanvasRenderingContext2D.prototype.getImageData = function(x, y, w, h) {{
                const imageData = originalGetImageData.apply(this, arguments);
                for (let i = 0; i < imageData.data.length; i += 4) {{
                    imageData.data[i] = imageData.data[i] + (Math.random() > 0.5 ? 1 : -1);
                }}
                return imageData;
            }};

            // WebGL Fingerprint Protection
            const originalGetParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(parameter) {{
                // Randomize Vendor and Renderer if requested
                if (parameter === 37445) return "Intel Inc."; // UNMASKED_VENDOR_WEBGL
                if (parameter === 37446) return "Intel(R) Iris(TM) Plus Graphics 640"; // UNMASKED_RENDERER_WEBGL
                return originalGetParameter.apply(this, arguments);
            }};

            // Audio Fingerprint Protection
            const originalGetChannelData = AudioBuffer.prototype.getChannelData;
            AudioBuffer.prototype.getChannelData = function() {{
                const channelData = originalGetChannelData.apply(this, arguments);
                for (let i = 0; i < channelData.length; i += 100) {{
                    channelData[i] = channelData[i] + (Math.random() * 0.0001);
                }}
                return channelData;
            }};

            // Battery API Mocking
            if (navigator.getBattery) {{
                const originalGetBattery = navigator.getBattery;
                navigator.getBattery = function() {{
                    return Promise.resolve({{
                        charging: true,
                        chargingTime: 0,
                        dischargingTime: Infinity,
                        level: 0.9 + Math.random() * 0.1,
                        onchargingchange: null,
                        onchargingtimechange: null,
                        ondischargingtimechange: null,
                        onlevelchange: null,
                        addEventListener: () => {{}},
                        removeEventListener: () => {{}},
                        dispatchEvent: () => {{}}
                    }});
                }};
            }}

            // Media Devices Mocking
            if (navigator.mediaDevices && navigator.mediaDevices.enumerateDevices) {{
                navigator.mediaDevices.enumerateDevices = function() {{
                    return Promise.resolve([
                        {{ deviceId: "default", kind: "audioinput", label: "Default Audio Input", groupId: "group1" }},
                        {{ deviceId: "default", kind: "videoinput", label: "FaceTime HD Camera", groupId: "group2" }},
                        {{ deviceId: "default", kind: "audiooutput", label: "Default Audio Output", groupId: "group1" }}
                    ]);
                }};
            }}

            // Screen Jitter
            const jitter = () => Math.floor(Math.random() * 10);
            Object.defineProperty(window, 'screen', {{
                get: () => ({{
                    width: {fingerprint['screen']['width']} + jitter(),
                    height: {fingerprint['screen']['height']} + jitter(),
                    availWidth: {fingerprint['screen']['width']},
                    availHeight: {fingerprint['screen']['height']},
                    colorDepth: 24,
                    pixelDepth: 24,
                }})
            }});
        """
