package org.apache.commons.csv;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.Reader;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import java.io.StringReader;
import java.lang.reflect.Field;

class ExtendedBufferedReader_7_1Test {

    @Test
    void testgetLineNumber_initialValue() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader("Line 1\nLine 2"));
        int lineNumber = invokeGetLineNumber(reader);
        Assertions.assertEquals(0, lineNumber);
    }

    @Test
    void testgetLineNumber_afterReading() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader("Line 1\nLine 2"));
        reader.readLine();
        int lineNumber = invokeGetLineNumber(reader);
        Assertions.assertEquals(1, lineNumber);
        
        reader.readLine();
        lineNumber = invokeGetLineNumber(reader);
        Assertions.assertEquals(2, lineNumber);
    }

    private int invokeGetLineNumber(ExtendedBufferedReader reader) throws Exception {
        Field lineCounterField = ExtendedBufferedReader.class.getDeclaredField("lineCounter");
        lineCounterField.setAccessible(true);
        return (int) lineCounterField.get(reader);
    }
}