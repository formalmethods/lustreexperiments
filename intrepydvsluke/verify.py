import intrepyd as ip
import intrepyd.tools as ts

def do_main():
    ctx = ip.Context()
    outputs = ts.translate_lustre(ctx, 'counter2.lus', 'top', 'float32')
    target = ctx.mk_not(outputs[0])
    br = ctx.mk_backward_reach()
    br.add_target(target)
    result = br.reach_targets()
    if result == ip.engine.EngineResult.REACHABLE:
        trace = br.get_last_trace()
        dataframe = trace.get_as_dataframe(ctx.net2name)
        print dataframe
    print result

if __name__ == "__main__":
    do_main()
