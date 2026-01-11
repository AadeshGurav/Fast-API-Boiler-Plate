# Design System Documentation

## Overview

This design system follows Material Design 3 principles while maintaining the existing purple gradient theme. All design decisions are stored as semantic tokens for consistency, maintainability, and scalability.

## Design Tokens

### Color System

#### Primary Palette (Purple Theme)
- `--color-primary-50` through `--color-primary-900`: Full primary color scale
- `--color-primary`: Main primary color (600)
- `--color-primary-dark`: Darker variant (700)
- `--color-primary-light`: Lighter variant (400)

#### Semantic Colors
- **Success**: `--color-success` (green scale 50-900)
- **Error**: `--color-error` (red scale 50-900)
- **Warning**: `--color-warning` (yellow scale 50-900)
- **Info**: `--color-info` (blue scale 50-900)

#### Surface Colors
- `--color-surface`: Primary surface color
- `--color-surface-variant`: Secondary surface color
- `--color-background`: Main background
- `--color-background-secondary`: Secondary background

#### Text Colors
- `--color-text-primary`: Main text color
- `--color-text-secondary`: Secondary text color
- `--color-text-muted`: Muted text color
- `--color-text-on-primary`: Text on primary background
- `--color-text-on-surface`: Text on surface
- `--color-text-on-error`: Text on error background

### Spacing System (8px Base Unit)

All spacing uses multiples of 8px:
- `--space-1`: 4px
- `--space-2`: 8px
- `--space-3`: 12px
- `--space-4`: 16px
- `--space-6`: 24px
- `--space-8`: 32px
- `--space-12`: 48px
- `--space-16`: 64px

Semantic tokens:
- `--space-xs`: Extra small (4px)
- `--space-sm`: Small (8px)
- `--space-md`: Medium (16px)
- `--space-lg`: Large (24px)
- `--space-xl`: Extra large (32px)
- `--space-2xl`: 2x large (48px)
- `--space-3xl`: 3x large (64px)

### Typography System

#### Font Families
- `--font-family-primary`: System font stack
- `--font-family-monospace`: Monospace font stack

#### Font Sizes
**Display:**
- `--font-size-display-large`: 56px
- `--font-size-display-medium`: 45px
- `--font-size-display-small`: 36px

**Headings:**
- `--font-size-heading-1`: 32px (h1)
- `--font-size-heading-2`: 28px (h2)
- `--font-size-heading-3`: 24px (h3)
- `--font-size-heading-4`: 20px (h4)
- `--font-size-heading-5`: 18px (h5)
- `--font-size-heading-6`: 16px (h6)

**Body:**
- `--font-size-body-large`: 16px
- `--font-size-body-medium`: 14px
- `--font-size-body-small`: 12px

**Caption:**
- `--font-size-caption-large`: 14px
- `--font-size-caption-small`: 12px

#### Font Weights
- `--font-weight-regular`: 400
- `--font-weight-medium`: 500
- `--font-weight-semibold`: 600
- `--font-weight-bold`: 700

#### Line Heights
- `--line-height-tight`: 1.2
- `--line-height-normal`: 1.5
- `--line-height-relaxed`: 1.75

### Border & Radius

#### Border Widths
- `--border-width-1`: 1px
- `--border-width-2`: 2px
- `--border-width-4`: 4px

#### Border Radius
- `--border-radius-xs`: 4px
- `--border-radius-sm`: 8px
- `--border-radius-md`: 12px
- `--border-radius-lg`: 16px
- `--border-radius-xl`: 24px
- `--border-radius-full`: 9999px (pill shape)

### Shadows (Material Design Elevation)

- `--shadow-elevation-0`: No shadow
- `--shadow-elevation-1`: Level 1 (cards, buttons)
- `--shadow-elevation-2`: Level 2 (hover states)
- `--shadow-elevation-3`: Level 3 (dropdowns, modals)
- `--shadow-elevation-4`: Level 4 (high elevation)
- `--shadow-elevation-5`: Level 5 (maximum elevation)

### Transitions

#### Duration
- `--transition-duration-fast`: 150ms
- `--transition-duration-base`: 200ms
- `--transition-duration-slow`: 300ms

#### Easing
- `--transition-easing-standard`: Standard easing
- `--transition-easing-emphasized`: Emphasized easing
- `--transition-easing-decelerated`: Decelerated easing
- `--transition-easing-accelerated`: Accelerated easing

### Z-Index Scale

- `--z-index-base`: 0
- `--z-index-dropdown`: 1000
- `--z-index-sticky`: 1020
- `--z-index-fixed`: 1030
- `--z-index-modal-backdrop`: 1040
- `--z-index-modal`: 1050
- `--z-index-popover`: 1060
- `--z-index-tooltip`: 1070

## Component Tokens

### Buttons

#### Sizes
- `--button-height-sm`: 32px
- `--button-height-md`: 40px
- `--button-height-lg`: 48px

#### Variants
- Primary: Uses `--button-primary-bg`, `--button-primary-text`
- Secondary: Uses `--button-secondary-bg`, `--button-secondary-text`
- Outline: Uses `--button-outline-border`, `--button-outline-text`
- Text: Uses `--button-text-color`

### Cards

- `--card-padding`: Standard padding (24px)
- `--card-border-radius`: 16px
- `--card-elevation`: Level 1 shadow
- `--card-elevation-hover`: Level 2 shadow

### Forms

- `--input-height-md`: 40px
- `--input-border-radius`: 12px
- `--input-border-color-focus`: Primary color
- `--input-border-color-error`: Error color
- `--label-font-size`: 12px
- `--label-font-weight`: 500

### Navigation

- `--nav-height`: 56px
- `--nav-link-padding-x`: 12px
- `--nav-link-padding-y`: 8px
- `--nav-link-color-active`: Primary color
- `--nav-link-bg-active`: Hover overlay

## Usage Guidelines

### Color Usage

1. **Primary Colors**: Use for primary actions, links, and brand elements
2. **Semantic Colors**: 
   - Success: Confirmations, positive states
   - Error: Errors, destructive actions
   - Warning: Warnings, caution states
   - Info: Informational messages
3. **Surface Colors**: Backgrounds and containers
4. **Text Colors**: Always ensure WCAG AA contrast (4.5:1 minimum)

### Spacing Guidelines

1. Always use spacing tokens, never hardcoded values
2. Use semantic tokens (`--space-md`) over numeric tokens (`--space-4`) when possible
3. Maintain 8px grid alignment
4. Use 4px increments for fine adjustments

### Typography Guidelines

1. Use heading sizes for hierarchy (h1-h6)
2. Body text should be 16px minimum for readability
3. Use appropriate line heights for text blocks
4. Limit font weights to 2-3 per page

### Component Usage

1. **Buttons**: Use size tokens for consistency
2. **Cards**: Use elevation tokens for depth
3. **Forms**: Use form tokens for consistent input styling
4. **Navigation**: Use nav tokens for active states

## Accessibility

### Color Contrast
- All text must meet WCAG AA standards (4.5:1)
- Interactive elements must have 3:1 contrast
- Never rely on color alone to convey meaning

### Focus Indicators
- All interactive elements must have visible focus states
- Use `:focus-visible` for keyboard navigation
- Focus indicators should use primary color

### Keyboard Navigation
- All interactive elements must be keyboard accessible
- Tab order should be logical
- Skip links for main content

## File Structure

```
app/static/css/demo/
├── tokens.css              # Core design tokens
├── component-tokens.css     # Component-specific tokens
├── base.css                 # Base styles using tokens
├── components.css           # Component styles
├── layout.css               # Layout styles
├── features.css             # Feature-specific styles
└── utilities.css            # Utility classes
```

## Migration Notes

### Legacy Variables
Legacy `--demo-*` variables are maintained for backward compatibility and map to new tokens. New code should use the new token system directly.

### Breaking Changes
None - all changes are backward compatible through legacy variable mappings.

## Best Practices

1. **Always use tokens**: Never hardcode colors, spacing, or typography values
2. **Semantic naming**: Use semantic tokens (`--color-primary`) over specific values
3. **Consistency**: Use the same token for the same purpose across components
4. **Documentation**: Update this document when adding new tokens
5. **Testing**: Verify contrast ratios and accessibility compliance

## Examples

### Using Color Tokens
```css
.button-primary {
  background-color: var(--color-primary);
  color: var(--color-text-on-primary);
}

.button-primary:hover {
  background-color: var(--color-primary-dark);
}
```

### Using Spacing Tokens
```css
.card {
  padding: var(--space-lg);
  margin-bottom: var(--space-md);
}
```

### Using Typography Tokens
```css
.heading {
  font-size: var(--font-size-heading-2);
  font-weight: var(--font-weight-bold);
  line-height: var(--line-height-tight);
}
```

