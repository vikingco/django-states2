import os
from optparse import make_option
from yapgvb import Graph

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db.models import get_model


class Command(BaseCommand):
    help = '''Generates a graph of available state machines'''
    option_list = BaseCommand.option_list + (
        make_option('--layout', '-l', action='store', dest='layout', default='dot',
            help='Layout to be used by GraphViz for visualization. Layouts: circo dot fdp neato twopi'),
        make_option('--format', '-f', action='store', dest='format', default='pdf',
            help='Format of the output file. Formats: pdf, jpg, png'),
    )
    args = '[model_label.field]'
    label = 'model name, i.e. mvno.subscription.state'

    def handle(self, *args, **options):
        if len(args) < 1:
            raise CommandError('need one or more arguments for model_name.field')

        for model_label in args:
            self.render_for_model(model_label, **options)

    def render_for_model(self, model_label, **options):
        app_label,model,field = model_label.split('.')
        Model = get_model(app_label, model)
        STATE_MACHINE = getattr(Model(), 'get_%s_machine' % field)()

        name = unicode(Model._meta.verbose_name)
        g = Graph('state_machine_graph_%s' % model_label, False)
        g.label = 'State Machine Graph %s' % name
        nodes = {}

        for state in STATE_MACHINE.states:
            nodes[state] = g.add_node(state,
                                      label=state.upper(),
                                      shape='rect',
                                      fontname='Arial')

        def find(f, a):
            for i in a:
                if f(i): return i
            return None

        for trion_name,trion in STATE_MACHINE.transitions.iteritems():
            edge = g.add_edge(nodes[trion.from_state], nodes[trion.to_state])
            edge.dir = 'forward'
            edge.arrowhead = 'normal'
            edge.label = '\n_'.join(trion.get_name().split('_'))
            edge.fontsize = 8
            edge.fontname = 'Arial'

            if getattr(trion, 'confirm_needed', False):
                edge.style = 'dotted'

            #if trion.next_function_name is not None:
            #    tr = find(lambda t: t.function_name == trion.next_function_name and t.from_state == trion.to_state, STATE_MACHINE.trions)
            #    while tr.next_function_name is not None:
            #        tr = find(lambda t: t.function_name == tr.next_function_name and t.from_state == tr.to_state, STATE_MACHINE.trions)

            #    if tr is not None:
            #        meta_edge = g.add_edge(nodes[trion.from_state], nodes[tr.to_state])
            #        meta_edge.arrowhead = 'empty'
            #        meta_edge.label = '\n_'.join(trion.function_name.split('_')) + '\n(compound)'
            #        meta_edge.fontsize = 8
            #        meta_edge.fontname = 'Arial'
            #        meta_edge.color = 'blue'

            #if any(lambda t: (t.next_function_name == trion.function_name), STATE_MACHINE.trions):
            #    edge.color = 'red'
            #    edge.style = 'dashed'
            #    edge.label += '\n(auto)'

        loc = 'state_machine_%s' % (model_label,)
        if options['create_dot']:
            g.write('%s.dot' % loc)

        g.layout(options['layout'])
        format = options['format']
        g.render(loc + '.' + format, format, None)
