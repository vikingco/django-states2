from django.template import Node, NodeList, Variable
from django.template import TemplateSyntaxError, VariableDoesNotExist
from django.template import Library

register = Library()


class CanMakeTransitionNode(Node):
    def __init__(self, object, transition_name, nodelist):
        self.object = object
        self.transition_name = transition_name
        self.nodelist = nodelist

    def render(self, context):
        object = Variable(self.object).resolve(context)
        transition_name = Variable(self.transition_name).resolve(context)
        user = Variable('request.user').resolve(context)

        if user and object.can_make_transition(transition_name, user):
            return self.nodelist.render(context)
        else:
            return ''


@register.tag
def can_make_transition(parser, token):
    """
    Conditional tag to validate whether it's possible to make a state
    transition (and the user is allowed to make the transition)

    Usage::

        {% can_make_transition object transition_name %}
           ...
        {% end_can_make_transition %}
    """
    # Parameters
    args = token.split_contents()

    # Read nodelist
    nodelist = parser.parse(('endcan_make_transition', ))
    parser.delete_first_token()

    # Return meta node
    return CanMakeTransitionNode(args[1], args[2], nodelist)
