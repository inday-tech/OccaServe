/**
 * Universal Signature Pad implementation for OccaServe
 * Uses PointerEvents for unified Mouse/Touch/Stylus support
 */
class SignaturePad {
    constructor(canvas, options = {}) {
        this.canvas = typeof canvas === 'string' ? document.getElementById(canvas) : canvas;
        if (!this.canvas) return;

        this.ctx = this.canvas.getContext('2d');
        this.isDrawing = false;
        this.listeners = {};
        this.options = options;

        this.init();
        this.refreshStyles();
    }

    init() {
        // Use PointerEvents for unified handling
        this.canvas.style.touchAction = 'none'; // Prevent scrolling while signing
        this.canvas.style.userSelect = 'none';

        this.canvas.addEventListener('pointerdown', (e) => this.startDrawing(e));
        this.canvas.addEventListener('pointermove', (e) => this.draw(e));
        window.addEventListener('pointerup', (e) => this.stopDrawing(e));
        window.addEventListener('pointercancel', (e) => this.stopDrawing(e));
    }

    refreshStyles() {
        if (!this.ctx) return;
        this.ctx.strokeStyle = this.options.penColor || '#1e293b';
        this.ctx.lineWidth = this.options.lineWidth || 3.5;
        this.ctx.lineJoin = 'round';
        this.ctx.lineCap = 'round';
    }

    getPosition(e) {
        const rect = this.canvas.getBoundingClientRect();
        // Use clientX/Y for consistency across all pointer types
        return {
            x: e.clientX - rect.left,
            y: e.clientY - rect.top
        };
    }

    startDrawing(e) {
        if (e.button !== 0 && e.pointerType === 'mouse') return; // Only left click

        this.isDrawing = true;
        this.canvas.setPointerCapture(e.pointerId);

        this.refreshStyles();
        const pos = this.getPosition(e);
        this.ctx.beginPath();
        this.ctx.moveTo(pos.x, pos.y);
        this.trigger('beginStroke');
    }

    draw(e) {
        if (!this.isDrawing) return;

        const pos = this.getPosition(e);
        this.ctx.lineTo(pos.x, pos.y);
        this.ctx.stroke();
    }

    stopDrawing(e) {
        if (this.isDrawing) {
            this.isDrawing = false;
            // Finish current path
            this.ctx.closePath();
            if (e && e.pointerId) {
                try { this.canvas.releasePointerCapture(e.pointerId); } catch (err) { }
            }
            this.trigger('endStroke');
            this.trigger('change');
        }
    }

    clear() {
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        this.refreshStyles();
        this.trigger('change');
    }

    isEmpty() {
        const blank = document.createElement('canvas');
        blank.width = this.canvas.width;
        blank.height = this.canvas.height;
        return this.canvas.toDataURL() === blank.toDataURL();
    }

    toDataURL() {
        return this.canvas.toDataURL('image/png');
    }

    getSignatureData() {
        return this.toDataURL();
    }

    addEventListener(event, callback) {
        if (!this.listeners[event]) this.listeners[event] = [];
        this.listeners[event].push(callback);
    }

    trigger(event) {
        if (this.listeners[event]) {
            this.listeners[event].forEach(cb => cb());
        }
    }
}
