import intrepyd as ip
import intrepyd.tools as ts

def do_main():
    ctx = ip.Context()
    outputs = ts.translate_lustre(ctx, 'counter.lus', 'counter', 'float32')
    ts.simulate(ctx, 'counter.lus', 10, outputs)

if __name__ == "__main__":
    do_main()
