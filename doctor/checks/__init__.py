"""Группы проверок. Каждый модуль экспортирует GROUP (id группы) и run(ctx)."""

from doctor.checks import distro, gpu, multilib, vulkan

# Порядок важен: следующие группы используют то, что предыдущие записали в контекст.
ALL_GROUPS = [distro, gpu, vulkan, multilib]
