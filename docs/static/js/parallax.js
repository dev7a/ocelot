// Enhanced parallax scrolling effect for hero section
(function() {
  'use strict';
  
  function initParallax() {
    const hero = document.getElementById('hero-parallax');
    if (!hero) {
      return; // Hero element not found, exit silently
    }
    
    // Check if user prefers reduced motion
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (prefersReducedMotion) {
      return; // Respect user preference for reduced motion
    }
    
    let ticking = false;
    
    function updateParallax() {
      const scrolled = window.scrollY;
      
      // Calculate parallax effect
      // Adjust parallax speed based on screen size
      const parallaxSpeed = window.innerWidth <= 768 ? 0.3 : 0.7; // Slower for smaller screens
      const yPos = scrolled * parallaxSpeed;
      
      // Apply the parallax effect
      const newPosition = `center ${-yPos}px`;
      hero.style.backgroundPosition = newPosition;
      
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
    
    // Add scroll listener with passive option for better performance
    window.addEventListener('scroll', requestTick, { passive: true });
    
    // Test the function immediately
    updateParallax();
    
    // Cleanup on page unload
    window.addEventListener('beforeunload', function() {
      window.removeEventListener('scroll', requestTick);
    });
  }
  
  // Initialize when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initParallax);
  } else {
    initParallax();
  }
})(); 