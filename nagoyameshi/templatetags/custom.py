from django import template
register = template.Library()

@register.filter
def get_value(value, key):
    if (key in value.keys()):
        print("-----------------------------")
        print(key)
        print(value)
        print(value[key])
        print("-----------------------------")
        
        return value[key]
    else:
        return None

@register.filter
def check_rsv(value1, value2):

    result = value1 / value2
    print(result)

    if result < 0.6:
        return('○')
    elif result >= 0.6 and result < 0.8:
        return('△')
    else:
        return('×')

@register.simple_tag
def check_rsv_bool(value1, value2):

    result = value1 / value2
    print(result)

    if result < 0.6:
        return(True)
    elif result >= 0.6 and result < 0.8:
        return(True)
    else:
        return(False)

@register.filter(name="multiply")
def multiply(value, quantity):
    return value * quantity