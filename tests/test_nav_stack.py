from bot.navigation.nav_stack import NavStack, Node


def test_nav_stack_basic_operations():
    user_data = {}
    stack = NavStack(user_data)

    # initial stack created under NAV_STACK_KEY
    assert user_data["nav_stack"] == []

    node1 = Node("level", 1, "Level 1")
    node2 = Node("term", 2, "Term 1")

    stack.push(node1)
    stack.push(node2)

    assert stack.peek() == node2
    assert stack.path_text() == "Level 1 / Term 1"
    assert stack.state() == [node1, node2]

    popped = stack.pop()
    assert popped == node2
    assert stack.peek() == node1
    assert stack.path_text() == "Level 1"

    assert stack.pop() == node1
    # popping from empty returns None
    assert stack.pop() is None
    assert stack.peek() is None
    assert stack.path_text() == ""

    # state should return a copy of nodes
    assert stack.state() == []
