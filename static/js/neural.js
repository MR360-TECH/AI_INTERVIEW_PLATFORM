/**
 * Neural Network Background — AI Interview Platform
 * Animated floating nodes connected by lines, blue brand palette.
 * Mouse-interactive. Dark/light mode aware. Respects prefers-reduced-motion.
 */
(function () {
    'use strict';

    // Bail out for users who prefer reduced motion
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

    const canvas = document.getElementById('neural-bg');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    let nodes = [];
    let animId = null;
    let mouse = { x: -9999, y: -9999 };

    // ── Colour palette (matches your blue brand) ─────────────────────────────
    function getColors() {
        const isDark = document.documentElement.classList.contains('dark-theme');
        return isDark
            ? { node: 'rgba(96, 165, 250, 0.75)', line: 'rgba(59, 130, 246, ', bg: 'transparent' }
            : { node: 'rgba(37, 99, 235, 0.5)',   line: 'rgba(37, 99, 235, ',  bg: 'transparent' };
    }

    // ── Node class ────────────────────────────────────────────────────────────
    class Node {
        constructor() { this.reset(true); }

        reset(init) {
            this.x  = Math.random() * canvas.width;
            this.y  = init ? Math.random() * canvas.height : -10;
            this.vx = (Math.random() - 0.5) * 0.38;
            this.vy = (Math.random() - 0.5) * 0.38;
            this.r  = Math.random() * 2 + 1;
            this.base = { x: this.x, y: this.y };
        }

        update() {
            // Mouse repulsion — nodes gently shy away from cursor
            const dx = this.x - mouse.x;
            const dy = this.y - mouse.y;
            const dist = Math.sqrt(dx * dx + dy * dy);
            if (dist < 100) {
                const force = (100 - dist) / 100 * 0.6;
                this.vx += (dx / dist) * force;
                this.vy += (dy / dist) * force;
            }

            // Speed cap
            const speed = Math.sqrt(this.vx * this.vx + this.vy * this.vy);
            if (speed > 1.2) {
                this.vx = (this.vx / speed) * 1.2;
                this.vy = (this.vy / speed) * 1.2;
            }

            this.x += this.vx;
            this.y += this.vy;

            // Bounce off edges
            if (this.x < 0 || this.x > canvas.width)  this.vx *= -1;
            if (this.y < 0 || this.y > canvas.height)  this.vy *= -1;

            this.x = Math.max(0, Math.min(canvas.width,  this.x));
            this.y = Math.max(0, Math.min(canvas.height, this.y));
        }

        draw(colors) {
            ctx.beginPath();
            ctx.arc(this.x, this.y, this.r, 0, Math.PI * 2);
            ctx.fillStyle = colors.node;
            ctx.fill();
        }
    }

    // ── Init ─────────────────────────────────────────────────────────────────
    function resize() {
        canvas.width  = window.innerWidth;
        canvas.height = window.innerHeight;
        // Node count scales with viewport area — capped for performance
        const count = Math.min(Math.floor((canvas.width * canvas.height) / 14000), 90);
        nodes = Array.from({ length: count }, () => new Node());
    }

    // ── Draw connections ─────────────────────────────────────────────────────
    const MAX_DIST = 160;

    function connectNodes(colors) {
        for (let i = 0; i < nodes.length; i++) {
            for (let j = i + 1; j < nodes.length; j++) {
                const dx   = nodes[i].x - nodes[j].x;
                const dy   = nodes[i].y - nodes[j].y;
                const dist = Math.sqrt(dx * dx + dy * dy);
                if (dist < MAX_DIST) {
                    const alpha = (1 - dist / MAX_DIST) * 0.45;
                    ctx.beginPath();
                    ctx.moveTo(nodes[i].x, nodes[i].y);
                    ctx.lineTo(nodes[j].x, nodes[j].y);
                    ctx.strokeStyle = colors.line + alpha + ')';
                    ctx.lineWidth   = 0.8;
                    ctx.stroke();
                }
            }
        }
    }

    // ── Animation loop ────────────────────────────────────────────────────────
    function animate() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        const colors = getColors();
        nodes.forEach(n => { n.update(); n.draw(colors); });
        connectNodes(colors);
        animId = requestAnimationFrame(animate);
    }

    // ── Events ────────────────────────────────────────────────────────────────
    window.addEventListener('mousemove', e => {
        mouse.x = e.clientX;
        mouse.y = e.clientY;
    });

    window.addEventListener('mouseleave', () => {
        mouse.x = -9999;
        mouse.y = -9999;
    });

    let resizeTimer;
    window.addEventListener('resize', () => {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(() => { resize(); }, 150);
    });

    // Re-colour when theme toggles
    const observer = new MutationObserver(() => { /* colors fetched live in animate */ });
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });

    // ── Boot ─────────────────────────────────────────────────────────────────
    resize();
    animate();
})();
