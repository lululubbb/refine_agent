package org.apache.commons.csv;
import java.io.BufferedReader;
import java.io.IOException;
import java.io.Reader;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;

import java.io.StringReader;
import java.lang.reflect.Field;
import java.lang.reflect.Method;

class ExtendedBufferedReader_3_4Test {

    @Test
    void testreadAgain_initialValue() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader("test"));
        setPrivateField(reader, "lastChar", -2);
        
        int result = invokePrivateMethod(reader, "readAgain");
        
        Assertions.assertEquals(-2, result);
    }

    @Test
    void testreadAgain_afterReading() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader("test"));
        setPrivateField(reader, "lastChar", 97); // ASCII for 'a'
        
        int result = invokePrivateMethod(reader, "readAgain");
        
        Assertions.assertEquals(97, result);
    }

    private void setPrivateField(ExtendedBufferedReader reader, String fieldName, int value) throws Exception {
        Field field = ExtendedBufferedReader.class.getDeclaredField(fieldName);
        field.setAccessible(true);
        field.setInt(reader, value);
    }

    private int invokePrivateMethod(ExtendedBufferedReader reader, String methodName) throws Exception {
        Method method = ExtendedBufferedReader.class.getDeclaredMethod(methodName);
        method.setAccessible(true);
        return (int) method.invoke(reader);
    }
}