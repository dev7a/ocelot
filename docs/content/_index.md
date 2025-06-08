---
title: ocelot
toc: false
showTitle: false
---

<div class="hero-section" id="hero-parallax">
  <div class="hero-content">
    <h1 class="hero-title">OCELOT</h1>
    <div class="hero-cta">
      <a href="/ocelot/docs/quickstart" class="hero-button hero-button-primary">Get Started</a>
      <a href="/ocelot/docs/architecture" class="hero-button hero-button-secondary">Architecture</a>
    </div>
    <p class="hero-description">A fast, flexible way to build custom AWS Lambda Extension Layers for the OpenTelemetry Collector.</p>
  </div>
</div>

<script>
// Enhanced parallax scrolling effect with debugging
(function() {
  console.log('Parallax script loading...');
  
  // Wait for DOM to be ready
  function initParallax() {
    const hero = document.getElementById('hero-parallax');
    if (!hero) {
      console.log('Hero element not found');
      return;
    }
    
    console.log('Hero element found, initializing parallax...');
    
    // Check if user prefers reduced motion
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (prefersReducedMotion) {
      console.log('Reduced motion preferred, skipping parallax');
      return;
    }
    
    console.log('Parallax conditions met, setting up scroll listener...');
    
    let ticking = false;
    
    function updateParallax() {
      const scrolled = window.pageYOffset;
      const heroRect = hero.getBoundingClientRect();
      const heroTop = heroRect.top + scrolled;
      const heroHeight = heroRect.height;
      
      // Calculate parallax effect
      const parallaxSpeed = 0.3; // Slower for more subtle effect
      const yPos = scrolled * parallaxSpeed;
      
      // Apply the parallax effect
      const newPosition = `center ${-yPos}px`;
      hero.style.backgroundPosition = newPosition;
      
      // Debug output (remove in production)
      if (scrolled % 50 === 0) { // Log every 50px of scroll
        console.log(`Scroll: ${scrolled}px, BG Position: ${newPosition}`);
      }
      
      ticking = false;
    }
    
    function requestTick() {
      if (!ticking) {
        requestAnimationFrame(updateParallax);
        ticking = true;
      }
    }
    
    // Set initial background position
    hero.style.backgroundPosition = 'center 0px';
    console.log('Initial background position set');
    
    // Add scroll listener
    window.addEventListener('scroll', requestTick, { passive: true });
    console.log('Scroll listener added');
    
    // Test the function immediately
    updateParallax();
    
    // Cleanup on page unload
    window.addEventListener('beforeunload', function() {
      window.removeEventListener('scroll', requestTick);
      console.log('Parallax cleanup completed');
    });
  }
  
  // Initialize when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initParallax);
  } else {
    initParallax();
  }
})();
</script>

**Ocelot** (OpenTelemetry Collector Extension Layer Optimization Toolkit) is a toolkit designed to simplify the creation of custom AWS Lambda Extension Layers for the OpenTelemetry Collector. It helps you add specific observability components or optimize your collector for particular use cases without maintaining a complex fork.

Ocelot integrates with the official [OpenTelemetry Lambda project](https://github.com/open-telemetry/opentelemetry-lambda) by leveraging its Go build tag system. This allows for the seamless inclusion of custom elements.

It functions as both a powerful CLI for local development and a CI/CD pipeline on GitHub Actions, enabling you to build, customize, and publish layers to your own AWS account or contribute them back to the community.

## Get Started

{{< cards >}}
  {{< card link="docs/quickstart" title="Quickstart" icon="play" >}}
  {{< card link="docs/architecture" title="Architecture" icon="cog" >}}
  {{< card link="docs/components" title="Components" icon="cube" >}}
{{< /cards >}}

## Key Capabilities

- **Overlay Approach:** Avoids forking the upstream repository, reducing maintenance overhead.
- **Flexible Distributions:** Build tailored collector layers with pre-defined or custom component sets.
- **Multiple Build Options:** Use pre-built layers, build locally, or set up a fully automated pipeline in your own fork.
- **Automated Publishing:** Securely publish layers to multiple AWS regions and architectures using GitHub Actions and OIDC.
- **Customizable Configurations:** Package custom OpenTelemetry Collector `config.yaml` files within your layers.

## Quick Example

Define a custom distribution in `config/distributions.yaml`:

```yaml
distributions:
  my-custom-layer:
    description: "OTLP receiver + ClickHouse exporter for data analytics"
    base: minimal
    build-tags:
      - "lambdacomponents.exporter.clickhouse"
```

Build and publish your custom layer:

```bash
uv run tools/ocelot.py --distribution my-custom-layer
```

That's it! Ocelot will:
1. Clone the upstream OpenTelemetry Lambda repository
2. Apply your custom components as an overlay
3. Build a collector binary with only the components you need
4. Package it as a Lambda layer and publish to AWS

> [!NOTE]
> This is a work in progress, and the implementation is subject to change.

For more information, visit the [documentation]({{< relref "docs" >}}). 