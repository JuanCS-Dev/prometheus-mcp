"""Comprehensive edge case and real-world usage tests."""
import pytest
import subprocess
import tempfile
import os
import time
from pathlib import Path


class TestShellEdgeCases:
    
    def test_multiline_python_code(self):
        result = subprocess.run(
            ['python3', '-c', 'for i in range(3):\n    print(i)'],
            capture_output=True, text=True, timeout=5
        )
        assert result.returncode == 0
        assert '0' in result.stdout and '2' in result.stdout
    
    def test_command_with_pipes(self):
        result = subprocess.run(
            'echo "hello world" | wc -w',
            shell=True, capture_output=True, text=True, timeout=5
        )
        assert result.returncode == 0
        assert '2' in result.stdout
    
    def test_large_output_streaming(self):
        result = subprocess.run(
            ['python3', '-c', 'for i in range(1000): print(f"Line {i}")'],
            capture_output=True, text=True, timeout=5
        )
        assert result.returncode == 0
        lines = result.stdout.strip().split('\n')
        assert len(lines) == 1000
    
    def test_stderr_capture(self):
        result = subprocess.run(
            ['python3', '-c', 'import sys; sys.stderr.write("error\\n")'],
            capture_output=True, text=True, timeout=5
        )
        assert 'error' in result.stderr
    
    def test_special_chars_in_args(self):
        result = subprocess.run(
            ['echo', 'hello "world"', '$HOME'],
            capture_output=True, text=True, timeout=5
        )
        assert result.returncode == 0
        assert '$HOME' in result.stdout
    
    def test_long_command_line(self):
        long_arg = 'x' * 10000
        result = subprocess.run(
            ['echo', long_arg],
            capture_output=True, text=True, timeout=5
        )
        assert result.returncode == 0
        assert len(result.stdout.strip()) == 10000
    
    def test_nonexistent_command(self):
        with pytest.raises((subprocess.CalledProcessError, FileNotFoundError, OSError)):
            subprocess.run(
                ["nonexistent_xyz123"],
                capture_output=True, text=True, timeout=2, check=True
            )
    
    def test_permission_denied(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            no_exec = Path(tmpdir) / 'no_exec.sh'
            no_exec.write_text('#!/bin/bash\necho hello')
            no_exec.chmod(0o644)
            
            with pytest.raises((subprocess.CalledProcessError, PermissionError, FileNotFoundError, OSError)):
                subprocess.run([str(no_exec)], timeout=2, check=True)


class TestRealWorldUsage:
    
    def test_git_workflow(self):
        original_dir = os.getcwd()
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                os.chdir(tmpdir)
                subprocess.run(['git', 'init'], timeout=5, check=True, capture_output=True)
                subprocess.run(['git', 'config', 'user.email', 'test@test.com'], timeout=5, check=True)
                subprocess.run(['git', 'config', 'user.name', 'Test'], timeout=5, check=True)
                Path('test.txt').write_text('content')
                subprocess.run(['git', 'add', '.'], timeout=5, check=True)
                result = subprocess.run(
                    ['git', 'commit', '-m', 'Initial'],
                    capture_output=True, text=True, timeout=5
                )
                assert result.returncode == 0
        finally:
            os.chdir(original_dir)
    
    def test_python_script(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            script = Path(tmpdir) / 'script.py'
            script.write_text('print("hello")')
            result = subprocess.run(
                ['python3', str(script)],
                capture_output=True, text=True, timeout=5
            )
            assert result.returncode == 0
            assert 'hello' in result.stdout
    
    def test_file_operations(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / 'file1.txt').write_text('hello world')
            (Path(tmpdir) / 'file2.txt').write_text('goodbye world')
            
            result = subprocess.run(
                ['grep', '-r', 'world', tmpdir],
                capture_output=True, text=True, timeout=5
            )
            assert 'hello world' in result.stdout
    
    def test_env_vars(self):
        env = os.environ.copy()
        env['TEST_VAR'] = 'test_value'
        result = subprocess.run(
            ['bash', '-c', 'echo $TEST_VAR'],
            env=env, capture_output=True, text=True, timeout=5
        )
        assert 'test_value' in result.stdout
    
    def test_exit_codes(self):
        assert subprocess.run(['true'], timeout=5).returncode == 0
        assert subprocess.run(['false'], timeout=5).returncode != 0
        result = subprocess.run(['python3', '-c', 'import sys; sys.exit(42)'], timeout=5)
        assert result.returncode == 42


class TestConcurrency:
    
    def test_rapid_commands(self):
        start = time.time()
        for i in range(10):
            result = subprocess.run(['echo', f'test{i}'], capture_output=True, timeout=1)
            assert result.returncode == 0
        duration = time.time() - start
        assert duration < 2.0
    
    def test_timeout(self):
        with pytest.raises(subprocess.TimeoutExpired):
            subprocess.run(['sleep', '10'], timeout=0.5)


class TestUnicode:
    
    def test_unicode_io(self):
        unicode_text = "Hello 世界 🚀"
        result = subprocess.run(
            ['echo', unicode_text],
            capture_output=True, text=True, timeout=5
        )
        assert result.returncode == 0
