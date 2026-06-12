package org.apache.commons.csv;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.Reader;
import java.io.StringReader;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

class ExtendedBufferedReader_3_4Test {

    @Test
    void testreadAgain_initialValue() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader("test"));
        setPrivateField(reader, "lastChar", ExtendedBufferedReader.UNDEFINED);
        
        int result = invokePrivateMethod(reader, "readAgain");
        
        Assertions.assertEquals(ExtendedBufferedReader.UNDEFINED, result);
    }

    @Test
    void testreadAgain_afterReading() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader("test"));
        setPrivateField(reader, "lastChar", 97); // ASCII for 'a'
        
        int result = invokePrivateMethod(reader, "readAgain");
        
        Assertions.assertEquals(97, result);
    }

    @Test
    void testreadAgain_boundaryValue() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader("test"));
        setPrivateField(reader, "lastChar", ExtendedBufferedReader.END_OF_STREAM);
        
        int result = invokePrivateMethod(reader, "readAgain");
        
        Assertions.assertEquals(ExtendedBufferedReader.END_OF_STREAM, result);
    }

    @Test
    void testreadAgain_afterMultipleReads() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader("test"));
        setPrivateField(reader, "lastChar", 116); // ASCII for 't'
        
        int result = invokePrivateMethod(reader, "readAgain");
        
        Assertions.assertEquals(116, result);
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