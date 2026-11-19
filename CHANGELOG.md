# Changelog

All notable changes to this project are documented in this file. The release bot
writes each version's section from the commits (Conventional Commits) and the hand-written
Unreleased section.

## 0.2.0 - 2026-11-19

### Added

- **view:** sankey, problems only, patterns, change marks; clearer rings, treemap and tree

### Fixed

- **view:** treemap with its layered fills again, the BI order below the aggregations

## 0.1.0 - 2026-11-19

### Added

- **view:** tiles, one hexagon per aggregation, and impact, the hosts and services that drag the most aggregations down
- **view:** names bent along the rings in the pie and in the rings' wide segments
- **Breaking:** **view:** charts drawn with ECharts, five views besides the pie
- **view:** tree view labels, pills of hosts and services, legend bars

### Changed

- **Breaking:** bi_pie is now bi_charts
