import React, { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import '../styles/landing.css';

export default function LandingPage() {
  const containerRef = useRef(null);
  const [scrollProgress, setScrollProgress] = useState(0);
  const [isScrolled, setIsScrolled] = useState(false);
  const navigateTo = useNavigate();

  useEffect(() => {
    // Initialize Three.js scene
    let scene, camera, renderer, particles, mapLines;

    const initThreeScene = async () => {
      // Dynamically import Three.js
      const THREE = await import('three');

      const container = containerRef.current;
      if (!container) return;

      // Scene setup
      scene = new THREE.Scene();
      scene.background = new THREE.Color(0x0a0e27);

      camera = new THREE.PerspectiveCamera(
        75,
        window.innerWidth / window.innerHeight,
        0.1,
        1000
      );
      camera.position.z = 5;

      renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
      renderer.setSize(window.innerWidth, window.innerHeight);
      renderer.setClearColor(0x0a0e27, 0.2);
      renderer.setPixelRatio(window.devicePixelRatio);
      container.appendChild(renderer.domElement);

      // Create particle system
      const particleGeometry = new THREE.BufferGeometry();
      const particleCount = 1500;
      const positions = new Float32Array(particleCount * 3);
      const colors = new Float32Array(particleCount * 3);

      const colorOptions = [
        { r: 1.0, g: 0.2, b: 0.1 },      // Red
        { r: 0.2, g: 0.6, b: 1.0 },      // Blue
        { r: 0.0, g: 0.85, b: 1.0 },     // Cyan
        { r: 1.0, g: 0.4, b: 0.1 },      // Orange
      ];

      for (let i = 0; i < particleCount * 3; i += 3) {
        positions[i] = (Math.random() - 0.5) * 30;
        positions[i + 1] = (Math.random() - 0.5) * 30;
        positions[i + 2] = (Math.random() - 0.5) * 30;

        const color = colorOptions[Math.floor(Math.random() * colorOptions.length)];
        colors[i] = color.r;
        colors[i + 1] = color.g;
        colors[i + 2] = color.b;
      }

      particleGeometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
      particleGeometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));

      const particleMaterial = new THREE.PointsMaterial({
        size: 0.08,
        vertexColors: true,
        transparent: true,
        sizeAttenuation: true,
      });

      particles = new THREE.Points(particleGeometry, particleMaterial);
      scene.add(particles);

      // Create India map outline with lines
      const mapGeometry = new THREE.BufferGeometry();
      const mapVertices = [];
      const mapColors = [];

      // Simplified India map coordinates
      const indiaOutline = [
        [0.15, 0.25], [0.22, 0.20], [0.30, 0.18], [0.38, 0.20],
        [0.45, 0.18], [0.50, 0.22], [0.55, 0.25], [0.60, 0.30],
        [0.62, 0.40], [0.58, 0.48], [0.50, 0.52], [0.42, 0.55],
        [0.35, 0.52], [0.28, 0.48], [0.22, 0.42], [0.18, 0.35],
        [0.15, 0.25]
      ];

      for (let i = 0; i < indiaOutline.length; i++) {
        const [x, y] = indiaOutline[i];
        mapVertices.push((x - 0.5) * 10, (y - 0.5) * 8, Math.random() * 0.5);
        mapColors.push(0.0, 0.85, 1.0); // Cyan
      }

      mapGeometry.setAttribute('position', new THREE.BufferAttribute(new Float32Array(mapVertices), 3));
      mapGeometry.setAttribute('color', new THREE.BufferAttribute(new Float32Array(mapColors), 3));

      const mapMaterial = new THREE.LineBasicMaterial({
        vertexColors: true,
        transparent: true,
        linewidth: 3,
      });

      mapLines = new THREE.LineLoop(mapGeometry, mapMaterial);
      scene.add(mapLines);

      // Add weather event points on map
      const eventGeometry = new THREE.BufferGeometry();
      const eventPositions = [];
      const eventColors = [];
      const weatherEvents = [
        [0.30, 0.35], [0.45, 0.25], [0.55, 0.40], [0.25, 0.28],
        [0.50, 0.45], [0.35, 0.52], [0.60, 0.35]
      ];

      weatherEvents.forEach(([x, y]) => {
        eventPositions.push((x - 0.5) * 10, (y - 0.5) * 8, 0.2);
        eventColors.push(1.0, 0.3, 0.1); // Red for events
      });

      eventGeometry.setAttribute('position', new THREE.BufferAttribute(new Float32Array(eventPositions), 3));
      eventGeometry.setAttribute('color', new THREE.BufferAttribute(new Float32Array(eventColors), 3));

      const eventMaterial = new THREE.PointsMaterial({
        size: 0.3,
        vertexColors: true,
        transparent: true,
        sizeAttenuation: true,
      });

      const eventPoints = new THREE.Points(eventGeometry, eventMaterial);
      scene.add(eventPoints);

      // Handle scroll
      const onScroll = () => {
        const scrollTop = window.scrollY;
        const docHeight = document.documentElement.scrollHeight - window.innerHeight;
        const scrollPercent = scrollTop / docHeight;
        setScrollProgress(scrollPercent);
        setIsScrolled(scrollTop > 50);

        if (scene) {
          scene.rotation.x = scrollPercent * Math.PI * 0.3;
          scene.rotation.z = scrollPercent * Math.PI * 0.15;
        }
      };

      // Handle resize
      const onWindowResize = () => {
        if (!camera || !renderer) return;
        camera.aspect = window.innerWidth / window.innerHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(window.innerWidth, window.innerHeight);
      };

      // Animation loop
      const animate = () => {
        requestAnimationFrame(animate);

        if (particles) {
          particles.rotation.x += 0.00008;
          particles.rotation.y += 0.00015;
        }

        if (mapLines) {
          mapLines.rotation.x += 0.0001;
          mapLines.rotation.y += 0.00008;
        }

        if (renderer && scene && camera) {
          renderer.render(scene, camera);
        }
      };

      window.addEventListener('scroll', onScroll);
      window.addEventListener('resize', onWindowResize);

      animate();

      return () => {
        window.removeEventListener('scroll', onScroll);
        window.removeEventListener('resize', onWindowResize);
        if (renderer && container && container.contains(renderer.domElement)) {
          renderer.dispose();
          container.removeChild(renderer.domElement);
        }
      };
    };

    initThreeScene();
  }, []);

  return (
    <div className="landing-page">
      <div className="canvas-container" ref={containerRef} />

      {/* Navigation */}
      <nav className={`nav-header ${isScrolled ? 'scrolled' : ''}`}>
        <div className="nav-content">
          <div className="logo" onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}>
            <div className="logo-icon">🌩️</div>
            <span className="logo-text">WeatherAPI</span>
          </div>
          <div className="nav-links">
            <a href="#features" className="nav-link">Features</a>
            <a href="#metrics" className="nav-link">Metrics</a>
            <a href="#tech" className="nav-link">Technology</a>
            <a href="#footer" className="nav-link">Contact</a>
          </div>
          <div className="nav-actions">
            <button className="nav-btn nav-btn-secondary" onClick={() => navigateTo('/login')}>
              Login
            </button>
            <button className="nav-btn nav-btn-primary" onClick={() => navigateTo('/login')}>
              Start Now
            </button>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <div className="landing-content">
        {/* Hero Section */}
        <section className="hero-section">
          <div className="hero-container">
            <div className="hero-content">
              <div className="hero-label">🚀 NEXT-GENERATION WEATHER INTELLIGENCE</div>
              <h1 className="hero-title">
                Unified <span className="gradient-text">Weather</span> Intelligence for India
              </h1>
              <p className="hero-subtitle">
                Real-time aggregation of weather data from multiple sources. Track, analyze, and verify weather events across all 28 states with precision-driven ML algorithms.
              </p>
              <div className="hero-buttons">
                <button className="btn btn-primary" onClick={() => navigateTo('/login')}>
                  Access Dashboard
                </button>
                <button className="btn btn-secondary">
                  View Documentation
                </button>
              </div>
            </div>
            <div className="hero-visuals">
              <div className="stats-grid">
                <div className="stat-card">
                  <div className="stat-number">250+</div>
                  <div className="stat-label">Weather Events</div>
                </div>
                <div className="stat-card">
                  <div className="stat-number">28</div>
                  <div className="stat-label">States Covered</div>
                </div>
                <div className="stat-card">
                  <div className="stat-number">4</div>
                  <div className="stat-label">Data Sources</div>
                </div>
                <div className="stat-card">
                  <div className="stat-number">99.9%</div>
                  <div className="stat-label">Uptime</div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Features Section */}
        <section id="features" className="features-section">
          <div className="section-header">
            <h2>Powerful Capabilities</h2>
            <p>Advanced weather intelligence and real-time data processing</p>
          </div>
          <div className="features-grid">
            <div className="feature-card">
              <div className="feature-icon">📡</div>
              <h3>Multi-Source Collection</h3>
              <p>Aggregate real-time data from Twitter/X, news websites, OpenWeather API, and verified citizen reports all in one place.</p>
            </div>
            <div className="feature-card">
              <div className="feature-icon">🗺️</div>
              <h3>Interactive India Map</h3>
              <p>Visualize weather events across all Indian states with color-coded severity indicators and geolocation precision.</p>
            </div>
            <div className="feature-card">
              <div className="feature-icon">📊</div>
              <h3>Real-Time Analytics</h3>
              <p>Track events by type, severity, state, and source with dynamic Recharts visualizations and detailed breakdowns.</p>
            </div>
            <div className="feature-card">
              <div className="feature-icon">🤖</div>
              <h3>ML-Powered Intelligence</h3>
              <p>Advanced algorithms for fake detection, automatic categorization, and duplicate event identification.</p>
            </div>
            <div className="feature-card">
              <div className="feature-icon">👥</div>
              <h3>Citizen Reports</h3>
              <p>Crowdsourced weather observations with photo/video evidence, location metadata, and verification workflows.</p>
            </div>
            <div className="feature-card">
              <div className="feature-icon">✅</div>
              <h3>Admin Verification</h3>
              <p>Comprehensive verification pipeline with ML-assisted review, approval workflow, and quality metrics.</p>
            </div>
          </div>
        </section>

        {/* Metrics Section */}
        <section id="metrics" className="metrics-section">
          <div className="section-header">
            <h2>Dashboard Analytics</h2>
            <p>Comprehensive insights into India's weather patterns</p>
          </div>
          <div className="metrics-grid">
            <div className="metric-card">
              <div className="metric-icon">📈</div>
              <div className="metric-value">Events Over Time</div>
              <div className="metric-title">Temporal Trends</div>
              <div className="metric-desc">Track weather events with granular time-based analytics</div>
            </div>
            <div className="metric-card">
              <div className="metric-icon">🔥</div>
              <div className="metric-value">Severity Heatmap</div>
              <div className="metric-title">Geographic Impact</div>
              <div className="metric-desc">High-severity events across Indian states</div>
            </div>
            <div className="metric-card">
              <div className="metric-icon">🏙️</div>
              <div className="metric-value">Top Cities</div>
              <div className="metric-title">Event Hotspots</div>
              <div className="metric-desc">Cities with highest weather event concentration</div>
            </div>
            <div className="metric-card">
              <div className="metric-icon">📊</div>
              <div className="metric-value">Source Analytics</div>
              <div className="metric-title">Data Quality</div>
              <div className="metric-desc">Verification stats and reliability metrics by source</div>
            </div>
          </div>
        </section>

        {/* Capabilities Section */}
        <section className="capabilities-section">
          <div className="section-header">
            <h2>Why Choose WeatherAPI</h2>
            <p>Enterprise-grade weather intelligence platform</p>
          </div>
          <div className="capabilities-grid">
            <div className="capability-list">
              <div className="capability-item">
                <div className="capability-icon">🎯</div>
                <div className="capability-content">
                  <h3>Accurate Data</h3>
                  <p>Multi-source verification ensures data accuracy and reliability</p>
                </div>
              </div>
              <div className="capability-item">
                <div className="capability-icon">⚡</div>
                <div className="capability-content">
                  <h3>Real-Time Processing</h3>
                  <p>Instant data ingestion and processing with minimal latency</p>
                </div>
              </div>
              <div className="capability-item">
                <div className="capability-icon">🔒</div>
                <div className="capability-content">
                  <h3>Secure & Compliant</h3>
                  <p>Enterprise-level security with JWT authentication and data protection</p>
                </div>
              </div>
              <div className="capability-item">
                <div className="capability-icon">📱</div>
                <div className="capability-content">
                  <h3>Fully Responsive</h3>
                  <p>Works seamlessly on desktop, tablet, and mobile devices</p>
                </div>
              </div>
            </div>
            <div className="capability-visual">
              <div className="capability-visual-icon">🌍</div>
            </div>
          </div>
        </section>

        {/* Tech Stack Section */}
        <section id="tech" className="tech-stack-section">
          <div className="section-header">
            <h2>Enterprise Technology Stack</h2>
            <p>Built with cutting-edge technologies for scalability and reliability</p>
          </div>
          <div className="tech-stack-grid">
            <div className="tech-category">
              <div className="tech-category-icon">🐍</div>
              <h3>Backend</h3>
              <ul>
                <li>FastAPI (Python 3.11+)</li>
                <li>PostgreSQL 16 Database</li>
                <li>SQLAlchemy 2.0 ORM</li>
                <li>Async Operations</li>
                <li>scikit-learn ML Models</li>
              </ul>
            </div>
            <div className="tech-category">
              <div className="tech-category-icon">⚛️</div>
              <h3>Frontend</h3>
              <ul>
                <li>React 18 + Vite</li>
                <li>Tailwind CSS</li>
                <li>Leaflet Maps</li>
                <li>Recharts Visualization</li>
                <li>Three.js Graphics</li>
              </ul>
            </div>
            <div className="tech-category">
              <div className="tech-category-icon">🚀</div>
              <h3>Infrastructure</h3>
              <ul>
                <li>Docker Compose</li>
                <li>CI/CD Pipeline</li>
                <li>JWT Authentication</li>
                <li>REST API Architecture</li>
                <li>Cloud Ready</li>
              </ul>
            </div>
          </div>
        </section>

        {/* CTA Section */}
        <section className="cta-section">
          <div className="cta-content">
            <h2>Ready to Transform Weather Intelligence?</h2>
            <p>Join India's most advanced weather data analytics platform today</p>
            <button className="btn btn-primary btn-large" onClick={() => navigateTo('/login')}>
              Get Started Now
            </button>
          </div>
        </section>

        {/* Footer */}
        <footer id="footer" className="landing-footer">
          <div className="footer-content">
            <div className="footer-section">
              <h4>WeatherAPI</h4>
              <p>National Weather Big Data Analytics Platform providing real-time weather intelligence for India.</p>
            </div>
            <div className="footer-section">
              <h4>Resources</h4>
              <ul>
                <li><a href="#docs">📖 Documentation</a></li>
                <li><a href="#api">⚙️ API Reference</a></li>
                <li><a href="#guides">📚 Guides</a></li>
                <li><a href="#blog">✍️ Blog</a></li>
              </ul>
            </div>
            <div className="footer-section">
              <h4>Community</h4>
              <ul>
                <li><a href="#github">🐙 GitHub</a></li>
                <li><a href="#twitter">𝕏 Twitter</a></li>
                <li><a href="#discord">💬 Discord</a></li>
                <li><a href="#email">📧 Support</a></li>
              </ul>
            </div>
            <div className="footer-section">
              <h4>Legal</h4>
              <ul>
                <li><a href="#privacy">🔒 Privacy Policy</a></li>
                <li><a href="#terms">📋 Terms of Service</a></li>
                <li><a href="#security">🛡️ Security</a></li>
              </ul>
            </div>
          </div>
          <div className="footer-bottom">
            <p>&copy; 2024 WeatherAPI. All rights reserved. | Designed with ❤️ for India</p>
          </div>
        </footer>
      </div>

      {/* Scroll Progress Indicator */}
      <div className="scroll-indicator">
        <div className="scroll-progress" style={{ width: `${scrollProgress * 100}%` }} />
      </div>
    </div>
  );
}
