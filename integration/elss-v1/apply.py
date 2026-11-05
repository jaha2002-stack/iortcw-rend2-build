#!/usr/bin/env python3
from pathlib import Path
import base64,gzip,hashlib,json,sys
src=Path(sys.argv[1]).resolve();ev=Path(sys.argv[2]).resolve();ev.mkdir(parents=True,exist_ok=True)
root=src/'SP/code/rend2'
sha=lambda b:hashlib.sha256(b).hexdigest()
before={p.relative_to(src).as_posix():p.read_bytes() for p in (src/'SP/code').rglob('*') if p.is_file()}
expected=json.loads((ev/'ELSS_V1_BASE_SHA256.json').read_text())
assert {p:sha(b) for p,b in before.items()}==expected and len(before)==1652

blob='''H4sIAKUH7GoC/8U9a3PjOI7f+1covmqv5SiOnX7cbBS5K53Hdmqcx8Tp7p3r8boUS4qV2JIiyXlskv9+AEhKpB52emavrmcrlkgIBEEABEGQu9l+o7W1fTu++R7OPO1g5k7S2J9oA/9qmmpDd+ZtDKe2E95re2GQxuFM+9bTWgeD4VDv4JfHdrCwZ1oUh54/cxMtdufhnauFwexRS1zE5jra5+GZdhk6ULKIPXsCYF4czrV06mYwiCuaPib+BLC5gooZUvG3RAvvAy0K/SDdvA/jmaMljKSJHaWL2E062gWg2ieaDcTE65NZmBqa48eAbnMWAuqNu3C2mLs5cs0OHM2ezbQQqIkBY5K6MXXD9gPsIaI7CiazhQMduXzU0nicTNzA7Uw0fz53Hd9OXeir7cF3WOl7s0nHDyZaEmp+CggDQLZIXOwtdTIG/gTa0eFgT4vtx825m0w37Xgy9VOgEnqjJbbnpo/a1J1FSMq9n07DRao5i2gG3En94ApxzZG4zTf/5bieH7gajsj4ePef49PvJwfnQ23rw8dy3dn56eHR4KCu9mjvV+3dVrlieHCwP9R+qaj4en64uwf4eluFWmxmPDg6PrrQWh/fQ7d73a33ehHDydfdwfjz7vBA6715kz5GLlRrSRovJqn29EaDf5OpHWs37uOPv38cmVRy507ejVMtjP0rP2BF3iy0U2Cm4y8SVgKSosWLIPXn7l4Iv4Z4Owoc98Hg8jEE8WDwt5dhOHNhqOz5pX+1CAWerDwAvt+5uwsYith1DBzFeZjiE4nVt0yqzDcvIL5JcnofuPEY0Ff3K0MMkuGYNV3FXoB+eEwBTW2zrXWt3a8Xp5r74CckCN96nXegGSAYj4bWs04PD0lXUNkMbcs6PeGMAqUCYcmRug7xxVSKkh/qkI9EZ86Ydr+iO5cLfyZhnRQa4er/oyRBvMeLIPGvAlA0hAZeCAIO/QdUDSIgSWEsJjKTtWScvUm4mSYAZumLrCf8G/4ufSV0RP0uI4B/x9+Xfkc9zinjDC9VDrkFtDZ6hqDKn9xwuZUKFnESxgBVgQPrZVpAk3M6mHrkgMNJqFKuQJMYMuBjO/qBAL+d7V58ySGUQRLsCK7cOIp9qYeZTDCQc9dGmWQv+36cZi+nd24MNN7D2N6FvqOdj4m0o8ALx14Li3RTqWEcq647cR/S2q887H5dbc1n525SVzW079y6j4DnTnXdAFQ3rylxS/Q+EVNxaxIGCZh/mq5AANvOTH/D1M73WmvOTHt+htqNPs48p1F6FIgCDya+3DINw0U8cUVdGtswjG6Qfp7BlCdKg3CfmmEWR6dG8F/sgrQH2q1nzxLXFG3jF9ySEu49QJWsWfvfh19290+/j4enX8/3DsZnoIVHw4uDk4vx2Zffh0d7uwO9AiEvYliJKWfMyHJdO3L6VjcjVLHHjGhRV7DIA3se6don7RYMlqttZ22+1PL+V/fxMIzJm6hgvkEa0gbrZHArNfT/7WZDAkW+cekmKWoqUz1827J67ruuZyQuYHT4W8bJtfKowyg/P68B9udn3sRO76O+ZCDqWKZzG00zZRi3fKtr+jvJWPngDCwnyCXIAzNT6+u+/B3NT8SJmq8Ggj+R1axFTUDJD58be/EPOhBt9MFRcnwHnKkOQPrp42ns4LS1ZtV3TgeSYBZcuFX4hDN5QpLCJITjLDBF/NsL5+OEbJjXwtHlbDcaTNi23zoNYzli3RTjg7KmUvWivF3Grn2TA+SVtUR4rNdExRKWVFDwIotJleK8TkIG58ewShDz2CsFRHyEojEvi4aoJqFgyuKUBnO+0b/xA2fNAvDxt24PJq3zXw/Ox/uDo398uagRAsc6H6OPPd4H2bODiTu8XdjQY2IC84mMuXjSS206O6S0+pPQV3o1mSY79Gv55gtMXy4D53C6gHeqBhcg8Uu0Y80mMws71tb7Ttdr018sbXEMfapep2IwbKJUgtaLA/AaAa4fAWxvpCpfnTy/SHIFTukAZpANcCnCmIb/cuZqczvaSCLw9dA+olBpUWYG8nVeQtMGW+JoQcjwt8G7jQAVOBghI6Oj/bawga4ECA8DLQVjHYOhSDQwxHNw3hKxAnBJBNEvBbiO8Hhr2cIGH9jC/tcwWgCjA64w9iQ5+dEdtd+vdz54eh1AbxXAlgDQlbmOszWfiXD24FMBuFQO+Y18CspmHWWmMWV9LbiaqKI4twBHJvOopTjJ/qjDWaGLOcUXg40e5ksFRV+jxI1TmSZlWpTWXLTKEnQq6xpGtOy7t8PSLCjPv4AYCU1gwEIaPj0jGOmkL60SyxAuQ+vvdPUnWQeLnOpbhTUDqL3imVpsoPJ2JZW2itjW180QLZ3CbXPuzsGPbIVGV/SlHYI0/AbqGAeT6PHfrRDMHBsSAcFKAAoeZM6iZxFmrhcsYq2NLfMb+A0hUBA9yiYuLJg4Wk65WgWBglt5W9QbNEk1ljTDbeQN6v2PZKDorw4Q2YLakmwIjnWhHf119K+vF74zFZKJPTDcRYbJLwwRQlDAwIJhb2Vv1BX2qGeA6pz5bNXNozgoIjDwbK3wyhC44KkyzBXuq2I0/CUGgy9nX2sySotXYTMKi2OwFhinaDZVWyLX/7Q14R+j+BbJNTKHfAJuUlrwrb3YdZnQ90xF9UXnSflR75HNGTkocxxdwX68gh9r1QzRnzJifJO5dJmzJWp2ulJ73Ao0C+gE7Ci3DnUQYA3qqogkrmaSXakFL1ibZXB65gmIYmlQS6tlERxha9wn3mk1cFLsqSiHlnLpljFzws7sdNpikhIuUpp0EI8hi1Cy8MBbFlIjT//4CYE3RIiZGdFk823SQTLeJugi8eCHwRB9Yj/bjYYu9bq4aPzmxr73eFjUvgjo5cRRb9rg3FC4h0ifucFVOhWUMoDYvrdOvg4G5iwMrrQrkK3Y7xwia22H0BPKJoDpZkZEeGNBQbOJ4BbDCtoKnEdthRoja5Y3ifqAKBjuQxhVwk1Y+VCHN8sWyYPQdlpZIaCf+RM/ZYEPZepHcvMw0vr77shop+5DarRnfuAa7cS+g78ptFbVf0Yu+Q136EGGgUFBRdBXaqJCOog/XLjwWTdw5BiiJbwUissA0WeAl0K/4OszJkln50cnF+PdwcBoIAHb4L6KTRDtbWJql3biYv/Qatvw63T+CGD5iOSoTnVmMNaAiudn3rrVFY/9QjydyKoduQJ933fPT45O/iFo9IM7ewY8FoQik0zNvwpwDkMCc9pYgIERh6NlkdK1sdX/GR/bM5ilWuTsMirXezoaNzA4LRpbFDkhaVjwg72MrL/90f2bWUU6taSYCmGK6owimIpKq8NxIfctsIIgWeOYUdX4I/gjbhhNFDnSgDUEen5OkokdwMijPDb2vxNSDRcETS5z+prVe37mL/Csg56FMMZOVVMovPVNoVkGnWRtwTJJaxjvdSoXxevvcxOkF1p6UoKvXgRq8DONy/28TCLt7QNAeRHrnhetWaVwbt4+k4UnbFcYk7/QOikx47HAxqgQbzvd/LlfmpgLbNHupyhIrVXUQBNYKC0H1E2BiAxNYHUNdAiYBZ+kD8weick7ygUy0qXQgbTWYn10A6eh68wvQKdKGfoZ+HUw9h+KI0wKB+Y86wUD1/5IoRNAC+iTXMv6KNUiFVBFEgVK14JnvW8JetlknrUouQlUZQC0ocLWULW0XewlYmrg7lVDau9VKHLwqJNvf1l2GvrUG4STa1BS5Pf+1iqWvpZ410n+AvWBSnKAdAZ9dYutgtLcHQ3I/Xz6E0zDvTx/VGYZK0dC1tK4Q3vpjHesom+JUljgLObf8WnI9+yKhkCspesIKxJEqzUrgDfJTc38d3k1wCSRAJgfD3NxhqzkiFsRcEnaZxThNviQSteszL6ovGZw0n6UxSc9nJ1gaqIpgwhQnYDnZ8K7zBdAMDDRbx2NtDxLjqCsB/A00RUgJFUOwRugcPs/ORuq/VnhIsztGQjg3HU2/WASzoE+H+N5wmPgvsI29KLsz6zcWDkIEqAJpjW2Mqj3EkfLfMHMYcpFeI2HKIa2h+hP7Dl0NxNl9MWwSK/ZPpE2KItLXFwFLEOkxDQkWdJXsBmmcZiPHC0EnyL2HZANx4fpMUaxCQONZbkAY2AeZn6ZJKxEqCULbjFaxbpXDEyBTSnsOFdtLhd2oOGj/6RTVlqXVjNYxU1+kCmv4ypcfHClaBUHbo20hPt5v1/yvLsP/+2xfwMQMQR+Wr1qEp5zyZMSGxJf7GRKSzLJfdYrXWJ5uJmkKWsvaqhoPF7elHevyY4rKrdCWCVTlotlWWQxrP82qZJXeQD+HyU3T2Po8pVHeVT+c/Jdb/dYkhyfSdFG8RCBGgeniICvhM4Jas7TZhAoMXn+0yw0pj7fMnN/vBsZMzu+wl2pLt9iRg8Ct6eliKsy6/ssVMofls78qmQnVjOHzTJ6CMtIDuWTsHP+nEb27cJtJbjQYYFrN6aG9l2cbRKlOApnj1dhcOp5wOAak50ZfPT6GA2fYdCdZDd4bBEtBnGo0uSjh3UD/LnZeQe+w43u/rgZWVMf/m7MQvhrFgGeGJ8fLIREj+Chz9ktNggt/m6KYXjINwcf+gyG7w1iVWZzGHR/68NHYAFV93sfuwWiJUCobDY54C/dGuZIvGFMqY/cMyb1t/i2IttXXIl1CCb6bGYH7m4yQMJ2pfRFxv0i3+s2vJTlrPAFKZ3tV/dR0pJ8idaOeDgNv2gL+TOybDOhOwrmqWJ8s4/ogzbXc7TG+r9KBuJf8pcR26MhWL6+ivgmzb+6D27vg/vhQ6+3EN2dfppuw1t90PDzwp85zDos72zBUqgpaRgJlWPkWSpF8oMN2cHgcLy3e7J/tL97cTAcGbTANa6NG/PyMQUZ5emt1dB5kJHZd0eYIPTqB6GBP1984yoOFxG80u8XX0TsoNduIoJ1qLgRWCG0REizKiNii2yRyptkAKab8BecA8wtFAsHxLTRx6UELGDAdogVxo5VqRV70IGYKUNLoVuXtkNkPGzppRhbaYeybNBDg3+NaxJd8kirDJQEWm2mdh3nDNOdL0JO84zRK5FdApn6RZCXwvZGvYkv99aYuEHqxiIpA79f3n1/Vad90dUsYaPGzNomaxutcosM8joZZ73d+eCZtpXV7rD+wtOn7Gkjq93OnvqMIQiXlW1kZdtd01m37LZtvmAmR7/39y20hewnJxZX8H2rSkMKYydpX7C+PsI0kUz4g2qRFwqYy70o0ZfLJ9ZdQ931TtBsSg1fj9YsScgA+Fp/wu5dW1aRhkz7r0eW2Nl2wieu7MIlK0YlsDfZlyDxEiXUmp/3ARDrTzw5KPY+J9Ew92dsS3UUjl2wslJHALPRvlwBBPhVtwhtzy0JrA1CeakKJp5jsCdpyzYuJVmUDQSTU+ryLXTplrp0q3TpdvT8fGtZudLcwke3zEgsUwKJ6tuRwT/S9aeSNmMVp6NcNxW6ZL7goIJ2dMl16Y5Qep+foaBHBb28YIsKtkboa0hSnQ8hDH425mRj+YbmC4ut8jq9bE8Lll+vkhVZVOpk4XK1LJhFg0wTw6SQxCGSyvWnvBrIKSzQqC7zX3NI1FmlVVNMY+vW5adLMp7foCTZfv8To51b+qcq417iYZV5LwG95JYlp5/2KYjenXfLOQDfcVQoPxx7JkSiqpdX9QpVW3kVF6zVHAdnySo5epGhjIaRY9FrXUd1c9iNwLPljhOXnxZtDs9CxTcKSWwS2pgHlxt+JcERuwtQoWb5J7QRTg4It55mPYTkohSilUm2TS9aKFTlQWzaC6mBKbk6ZliRA1X5sciNCH3qvpwDFPqjTpatIxCzqEGFt9qsQm80ixhFiconvRSnOIwxZMcMQ+x6juuhRfAcNfWDDl4dBA7x1nOU9WzLA78mdryZfZU0W+f7h+OT0++n54P949P9g8EzFgx//f3z6T/PTs8vdgdZGpns1+TxSebMDOXsHep9nsx87l7BQ/zYyhC9KebPVuTjPRWz8ORcpixiUarO0r6K9WoOWOlrluFURqtmL1nFapHEVKoo5CZVxGsITEr6kveRMXg2du5Fijsl+PFThc1mXc1GH8behdWY/hfylsrl0saS1asG4GqmL7cxIsDFRdOKxzA/sMTIhM+E8djz4yQdIgjPFAPxELLMSS+fAGhe2pMbgNi3U3ujz1HiLKhXJGTWARv+Rrl50j9Z/fbYQcphJk3JKl2UzBtF9UBfFIUUSrFKH9SFbTktkRpzHqxCRl8x/7FHG0UOC2g5LJzFaO/AcIw5P3gdSg5LHh8q/n0r/8iRjsEc28lNs9Vb7OzA17rebFaDISE/AGLUt7orYXZyGsbstMxQV7u0AgGoFJjQzba2Z89mrpMfqM2OBmaHaOnE4ATP5vie78YdfhJmDkv6hE5ialM70ezgDUu9pq0ufqawo/FjB1YXRCFJ8eBYfqIQD8tCS6YA2ulqfqKxY52UfV3a/+EksYm/Lom4zdHVJhBHOFgCqJ1RaLLjUBiqr7ElS6oyMwMwqlj/XFIyN3jRssTEiDZgCyYnkm1SOQC4DNqytmhnooIlaqrRUksW6Xk72XQN7TA3rBL/RitaLx7lLaY3lTYHq0J+zKngraJDSNktqhjQyFsbvHSj2G7G2KjSoVsrd0x257SMVWU4dg61JMzDRRQBRMJo34/te/T/hVDzVxJrFp3khBvFM66v7J/hG+xshlkI/nmreu4kZbssxsOzmqUOM++KPPXnZ/a7ZiGh6qeMGqvlYOg+jNN+/7chuFbj84PDg5OLo4vfT74eg207OrzQm0rZ8e7wV9pWJwRrllJJLluRyGwO8fiqQEyanrwDwQyvWrQk5tVsEuXszbIq9jRUVKMOrORsdee3dudbPciK0zTuS5FYhzi3GfxQLh7FVX3c69KUme1osRkzNwZ06NcfrVmEUpnKSqd9gRUWa02amK8tf71nXle0cy08VdbI9UZvZCkFI7PURAFIlMJUtbFRbIHHFmq7mnlkFT1gbHhhGd7KKWbJpS/g21Hh1teLBDF2FErBrbju++bGRpEdBWZAxyvYUcUMhHxRh4+NnlnRX97d+u2DQ/Trvvhpi4dFpn5KQQND3hthVx4weWs7fCdo2XHVwLVxrrc+9DACagBS89Ux5Dwgcm4/8ppW5X7hyEjoroxvvnt/yjaj8gKYae/t2DE4KUYTiND1J0EZkiSO4PEzdTvFsD87T3K82yo1I5CWmxP8YzOhxD5dYSYdBkSQjJsZXy2OfPmuvHqAXRkKIIGzDQekMK58gOAVd/RgPIDXSbJwz9zAAUfsHH7QuZ7PbYwY6fVL27zr3zAhWI1p/OQme1EWMyFs5n2hZ6RZf90qedWqgPPF4Qzx+PjN7NSN7dmWkU5hEKbhzDFIhZCr4sh1xdmj52f5oFJuR5kIDReXaYwB43zXtCRSDgU9kQZrP0zBsXIW8IFTFjEaEw66gzm37LEPupa3K7pBR5O6qIMKUkff4J+1PYE167DVww/WBUCn++4D9TkfCzwVQ/xYeaxLUQf8ZMc6Pjpp9bZ+QZqQuA8f8Sk7PdXuvP/grfc+6nr7tYA6DZCV3MYpa0MHmrs9uQddfEevx32inXDGnH7W5Xb2lAf6B37gfvMTzF0rG4D8UFnOc0ZGD3nHaBHt6Jucksx9ludzJl+6tMVTUBD9afmZARdWP5Rhd8eole4+wtRBH89AhQmsC/3Y1OhqpckshPbZvUX+XAPx99NEm4LkggnYpMWUnMpPFrJAVL+3lKxMFfK2tRZPZkx0E++s0Zx7QDkO3IdUyvfJe73CialsXNPeZomF4JcYitKrcyYPZIoe1tqt5EdXnpm5GctsFr9ipBQOkS8Reao2onL08GeGPOcdu/lKo9iMOmAlglvFkvWe/rbI1yVMKH4+KjGgPndJIFTmqj8179QtakULeURalPRLh2tXqRNjqh8GZpnTmwWh1Sv2QypkThAjR8efVqR3ZifcSYnJwcPQSH67FNIqp3cWKCl6D3X34vDhKJynppWkYS/S8FCJjRRHNBPi4gxb6Hh1NIOfTq44gEvrsOKh3MqAnC4TeZ7Fh3iJiLfsAlCrFFFLfhSaGLHgCs5vqwId7DxtvSTN7ch6m2iXCfx0f3nAZTq+wzQ5RXV82+l5WvZH12AxM2OR1cQCO8nD7lin5EIapeQigx/6DqW7BqSXnvyyRS/KrWZh4azykh7htV3QBfxPuv0MqZWHAF7ndAMePvGcb4tZ5NI56E+Nk92Lo28HWmO7QdVi1+BT4+z89Pj04mA/qyrsG3xqDE73dgffTgcZRE6TLLhGXbju08o43nbXQFH4JCe6fmp8PRnufjvYh1bZr77dwODK4OjkoLGaiRhyY4SiNIBafw4dscpJGPMoMQbTLvAVnAPg+sWXo+F4sHt8hrcLjD+f7v8+Pj0Z/E758ysjgZ8aGL5tbC+P//U+NU4PD6FXpycN1u2aOJ7gShU6vt+x3c1zov9SJHVZWnGeRAx0M1tdh0/r8Qz4l6XXeUmrqCRbQBmR4eeLJrFsSDFnMTXVVLtsr74QX0txNVc0sFXGtH5Ztcq8SuiyVRSj0Wgm0gJKX+61MWfQ1pKQznjacaqFnnLJJpuOuKtYchJf5TszuvSVM2DWJN37ScTABBhOWBpIzfwnyKhNMuPceEXzDBCP4OC8K+WnGloahhrl08Ij3oI2W2BW2KbjsoMvhhbGBOPZsdhWARzIuo52EipZ7pycjPxVEyVNTpmkWSUtZKsccdAwA8zzwrIiXc8TzWoO/uf1fIqR9iyUOjxzn/vreZWabObLX2VHzCzBg2WiSQxUBMGexbi9AoWLwCmJQAUJcnoPHZxbJQHU3KVPDqo28+c+bmbak6lbaK7Yp4q2MSOId1PWVSUdIh+r0GiizXiFjIJMs+tDGbGUSoNJzDMH1AOvjdOYRJqZbgfsllqm4VyPiacFycy7R0YxqjpmxwUiP2cXZTE0sySYeUaUqZyYk0+lVJw7qxMIGnblSmDQVJM4MkCG/ANZQTOouDBYnVk72lfJu0+liVnr0sqYV9l3iqIaODBsIjQqxrlijikG6eSrHQI8qNS+s2eUR4cuNy6h3FdNFtLyEdi0N3fGu/HVpKXvvMvOoObld62ezs7Ssj426iaCr4l95W7X8OW594yelSId2AVLbcikDimFWzrPA0Jw6g9ZGR+pJGijgZiBLGIAWBFx9EEcpuNQ3QykVwfSy0C2mDFcPc+IHrJznonWNbQe2nCkSVWGV69z/rSeyF4Zk4ZXqwsdpsWOV+SjyP5Zv6s/vWIjd612J3elWcJTXkzfmIrCXI3nL8Hw0PURmM9oyozHW4dBnbjNsqNo5gMGVObZozoAL0tsAi5MZP9aWcEDTTAni0vkOnxBQhMa41k3c5Q5DyWPuKTXyp2uT1lKQb2aVs7rS2MFyoz/VHPvT1R/4U+U3/TzCtl5Wb5okZy/GL9EVlJWiLilxNQqOIxRobrrbuXUjPblwvPc2EBEPz70YJ1aceVLOo8KJZf2jVrCz/xGsXvnY+5YfvBXFA3yy2Dw+ApPMzXoDu3lYbo/nTumi8PlrJNV16AUL2hRTqpy3hRg8ltGen8EeAkIrrHpQo7uLw9/BOJyjFXRA54hS+6ffCaJNaqv7PVT8bSRVU6EM8UVS/KZGylvXuor3VTBxRmfdX7LBddsdMbJx9L4TaqovnRKQZhMQz7hoJv5mYLCyYdrnSagiZ1WtHlntxqiBebSXY/ETXvVXzRI2LFI4SJVYq+xx+tYvf6Bu6HydTyvMKe03KUrrtGxm6LTdh/7aeoG3DzyE/pi3IS55DfqsOJ1JMPIqGfDvk43e1RC4vUjKEDvBeR789WXJVUAggILOHgEsA78VIOCZgtQeERQ+GmIM87foefskDOi5PpBQiXrsHSdVhFsJctTdx6FsR0/EpfBi7YBjbOc1aqJqTwuTjfHkE1XYPs/KxFZhp64VCFbkGp0P8XkRltE3CLHrod9Xk57mSScc17Ro6aAUbrVbFZgK44djrEAY+ch1Y/qBnPld6sXdsAgWCfdIU76/8MIAz7CdTyTztXnHa5jJvkoSleJVa+Q0xIc7R1lLVaiXc7CFZzwKAuTyXglOwS+TNJ4Dqej3U/dQLPvAA6v6+WzPfnb1Rei1DoX5CziiosRUHXriR9U3XnyUubNK0ap5MjJ9+yv2KpTLk9g3vxL7c38T8zJECdZ/q+8i6efcIgLa2Bp27VwD+fasnT3moCyvySgvCw5Prt8Z6lrD+uJ0GHiQZvIBt9hMVTJKPo6paA9idum8FrJQ/1f1tV8v8FoAAA='''
module=gzip.decompress(base64.b64decode(blob))
assert sha(module)=='6bc8c000611dd8c61cca12434581537f5792fb2e6c54bdcab51f3d2bc67d3439'
(root/'tr_elss.inc').write_bytes(module)

def replace(path,old,new,count=1):
    p=root/path;s=p.read_text();assert s.count(old)==count,(path,old[:100],s.count(old),count);p.write_text(s.replace(old,new))

replace('tr_scene.c','#include "tr_iflc.inc"','#include "tr_iflc.inc"\n#include "tr_elss.inc"')
replace('tr_scene.c','\tR_IFLC_Frame(fd);','\tR_IFLC_Frame(fd);\n\tR_ELSS_Frame(fd);')
replace('tr_scene.c','\tR_IFLC_CaptureShadowSlots(fd); // Read-only command diagnostics after actual allocation.','\tR_IFLC_CaptureShadowSlots(fd); // Read-only command diagnostics after actual allocation.\n\tR_ELSS_CaptureShadowSlots(fd);')

replace('tr_electric_fixture.inc','int R_ElectricFixtureForLight(const dlight_t *dl)\n{','int R_ElectricFixtureForLightAuto(const dlight_t *dl)\n{')
replace('tr_electric_fixture.inc','''unsigned int R_ElectricFixtureKey(int fixture)
{
    return fixture>0 && fixture<=s_efCount ? s_efFixtures[fixture-1].key : 0;
}
''','''int R_ElectricFixtureForLight(const dlight_t *dl)
{
    int fixture=0;
    if(R_ELSS_ElectricPolicy(dl,&fixture))return fixture;
    return R_ElectricFixtureForLightAuto(dl);
}
unsigned int R_ElectricFixtureKey(int fixture)
{
    if(fixture<0)return R_ELSS_ManualFixtureKey(fixture);
    return fixture>0 && fixture<=s_efCount ? s_efFixtures[fixture-1].key : 0;
}
''')
replace('tr_electric_fixture.inc','''static void RB_ElectricFixtureSurface(const drawSurf_t *ds)
{
    int i,entity,fixture=backEnd.viewParms.electricFixture;
    if (!s_efBuilt || fixture<=0 || fixture>s_efCount || !tr.world ||
''','''static void RB_ElectricFixtureSurface(const drawSurf_t *ds)
{
    int i,entity,fixture=backEnd.viewParms.electricFixture;
    if(fixture<0) {
        if ((backEnd.viewParms.flags & (VPF_SHADOWMAP|VPF_DEPTHSHADOW)) == (VPF_SHADOWMAP|VPF_DEPTHSHADOW) &&
            !(backEnd.viewParms.flags & (VPF_ORTHOGRAPHIC|VPF_FIREVOL_SYNTHETIC_SHADOW)) &&
            R_ELSS_SuppressManualDrawSurf(ds,fixture,backEnd.viewParms.electricFixtureKey)) return;
        goto original;
    }
    if (!s_efBuilt || fixture<=0 || fixture>s_efCount || !tr.world ||
''')

p=root/'tr_local.h';s=p.read_text()
assert s.count('extern cvar_t *r_dwFireLightControl;\n')==1
s=s.replace('extern cvar_t *r_dwFireLightControl;\n','extern cvar_t *r_dwFireLightControl;\nextern cvar_t *r_dwElectricLightControl;\n')
assert s.count('int R_ElectricFixtureForLight(const dlight_t *dl);\n')==1
s=s.replace('int R_ElectricFixtureForLight(const dlight_t *dl);\n','int R_ElectricFixtureForLightAuto(const dlight_t *dl);\nint R_ElectricFixtureForLight(const dlight_t *dl);\n')
anchor='void RB_SurfaceElectricTrim(srfBspSurface_t *srf, const unsigned char *omit, int triangleCount);\n'
assert s.count(anchor)==1
s=s.replace(anchor,anchor+'''void R_ELSS_ResetWorld(void);
void R_ELSS_Frame(const refdef_t *fd);
void R_ELSS_CaptureShadowSlots(const refdef_t *fd);
qboolean R_ELSS_ElectricPolicy(const dlight_t *dl,int *fixture);
unsigned int R_ELSS_ManualFixtureKey(int fixture);
qboolean R_ELSS_SuppressManualDrawSurf(const drawSurf_t *ds,int fixture,unsigned int key);
void R_ELSS_Select_f(void);
void R_ELSS_Next_f(void);
void R_ELSS_Info_f(void);
void R_ELSS_SelfPick_f(void);
void R_ELSS_Set_f(void);
void R_ELSS_Reset_f(void);
void R_ELSS_Save_f(void);
void R_ELSS_Reload_f(void);
void R_ELSS_List_f(void);
''')
p.write_text(s)

p=root/'tr_init.c';s=p.read_text()
a='cvar_t  *r_dwFireLightControl; // DARKWOLF_IFLC_V1, explicit opt-in master.\n';assert s.count(a)==1
s=s.replace(a,a+'cvar_t  *r_dwElectricLightControl; // DARKWOLF_ELSS_V1, electric own-body shadow control.\n')
a='\tr_dwFireLightControl = ri.Cvar_Get( "r_dwFireLightControl", "0", CVAR_ARCHIVE );\n\tri.Cvar_CheckRange(r_dwFireLightControl, 0.0f, 1.0f, qtrue);\n';assert s.count(a)==1
s=s.replace(a,a+'\tr_dwElectricLightControl = ri.Cvar_Get( "r_dwElectricLightControl", "0", CVAR_ARCHIVE );\n\tri.Cvar_CheckRange(r_dwElectricLightControl, 0.0f, 1.0f, qtrue);\n')
a='\tri.Cmd_AddCommand( "dw_fl_list", R_IFLC_List_f );\n';assert s.count(a)==1
s=s.replace(a,a+'''\tri.Cmd_AddCommand( "dw_el_select", R_ELSS_Select_f );
\tri.Cmd_AddCommand( "dw_el_self_pick", R_ELSS_SelfPick_f );
\tri.Cmd_AddCommand( "dw_el_next", R_ELSS_Next_f );
\tri.Cmd_AddCommand( "dw_el_info", R_ELSS_Info_f );
\tri.Cmd_AddCommand( "dw_el_set", R_ELSS_Set_f );
\tri.Cmd_AddCommand( "dw_el_reset", R_ELSS_Reset_f );
\tri.Cmd_AddCommand( "dw_el_save", R_ELSS_Save_f );
\tri.Cmd_AddCommand( "dw_el_reload", R_ELSS_Reload_f );
\tri.Cmd_AddCommand( "dw_el_list", R_ELSS_List_f );
''')
a='\tri.Cmd_RemoveCommand( "dw_fl_list" );\n';assert s.count(a)==1
s=s.replace(a,a+'''\tri.Cmd_RemoveCommand( "dw_el_select" );
\tri.Cmd_RemoveCommand( "dw_el_self_pick" );
\tri.Cmd_RemoveCommand( "dw_el_next" );
\tri.Cmd_RemoveCommand( "dw_el_info" );
\tri.Cmd_RemoveCommand( "dw_el_set" );
\tri.Cmd_RemoveCommand( "dw_el_reset" );
\tri.Cmd_RemoveCommand( "dw_el_save" );
\tri.Cmd_RemoveCommand( "dw_el_reload" );
\tri.Cmd_RemoveCommand( "dw_el_list" );
\tR_ELSS_ResetWorld();
''')
p.write_text(s)

replace('tr_bsp.c','\tR_ElectricFixtureReset();\n','\tR_ElectricFixtureReset();\n\tR_ELSS_ResetWorld();\n')

after={p.relative_to(src).as_posix():p.read_bytes() for p in (src/'SP/code').rglob('*') if p.is_file()}
changed=sorted(p for p in set(before)|set(after) if before.get(p)!=after.get(p))
expected_changed=[
 'SP/code/rend2/tr_bsp.c','SP/code/rend2/tr_electric_fixture.inc','SP/code/rend2/tr_elss.inc',
 'SP/code/rend2/tr_init.c','SP/code/rend2/tr_local.h','SP/code/rend2/tr_scene.c']
assert changed==expected_changed,changed
assert before['SP/code/rend2/tr_iflc.inc']==after['SP/code/rend2/tr_iflc.inc']
assert before['SP/code/rend2/tr_iflc_self.inc']==after['SP/code/rend2/tr_iflc_self.inc']
assert all(before[p]==after[p] for p in before if '/glsl/' in p)
proof={
 'base_run':41895006605,
 'base_commit':'728c023d0a9cc7f50c82843957f9d450c696b9b0',
 'purpose':'electric lamp own-body self-shadow control only',
 'changed':changed,
 'iflc_v15u_unchanged':True,
 'glsl_unchanged':True,
 'existing_electric_auto_preserved_as_auto':True,
 'manual_scope':'selected physical electric lamp own BSP body only',
 'shadow_slot_preserved':True,
 'direct_light_preserved':True,
 'local_volumetric_preserved':True,
 'other_casters_preserved':True,
 'profile_path':'electricshadows/<map>.elss'
}
(ev/'ELSS_V1_SOURCE_PROOF.json').write_text(json.dumps(proof,indent=2)+'\n')
(ev/'ELSS_V1_SOURCE_SHA256.json').write_text(json.dumps({p:sha(b) for p,b in after.items()},indent=2)+'\n')
print('ELSS_V1_APPLIED',changed)
