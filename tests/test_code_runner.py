from modules.code_runner import PythonCodeRunner


def test_execute_simple():
    runner = PythonCodeRunner(timeout=10)
    result = runner.execute("print('Hello, ONDES!')")
    assert "Hello, ONDES!" in result
    assert "Succès" in result


def test_execute_with_error():
    runner = PythonCodeRunner(timeout=10)
    result = runner.execute("raise ValueError('test error')")
    assert "Erreur" in result
    assert "test error" in result


def test_timeout():
    runner = PythonCodeRunner(timeout=2)
    result = runner.execute("import time; time.sleep(10)")
    assert "Timeout" in result


def test_math():
    runner = PythonCodeRunner(timeout=10)
    result = runner.execute("print(sum(range(100)))")
    assert "4950" in result
