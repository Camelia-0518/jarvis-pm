#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
集成模块

提供与外部系统的集成
"""

import os
os.environ['PYTHONIOENCODING'] = 'utf-8'

from .obsidian import ObsidianIntegration

__all__ = ['ObsidianIntegration']
