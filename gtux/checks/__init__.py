"""Группы проверок. Каждый модуль экспортирует GROUP (id группы) и run(ctx)."""

from gtux.checks import disks, distro, games, gpu, hardware, logs, multilib, proton, steam, tools, tuning, vulkan

# Порядок важен: следующие группы используют то, что предыдущие записали в контекст.
ALL_GROUPS = [distro, gpu, vulkan, multilib, steam, disks, proton, tools, tuning, hardware, games, logs]
