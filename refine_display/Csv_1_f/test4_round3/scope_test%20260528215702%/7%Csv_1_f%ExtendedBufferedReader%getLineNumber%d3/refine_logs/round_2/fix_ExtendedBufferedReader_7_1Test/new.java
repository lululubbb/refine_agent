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
    
    @Test
    void testgetLineNumber_emptyStream() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(""));
        int lineNumber = invokeGetLineNumber(reader);
        Assertions.assertEquals(0, lineNumber);
        
        reader.readLine();
        lineNumber = invokeGetLineNumber(reader);
        Assertions.assertEquals(0, lineNumber);
    }

    @Test
    void testgetLineNumber_variedContent() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader("Line 1\n\nLine 3\nLine 4"));
        reader.readLine(); // Line 1
        int lineNumber = invokeGetLineNumber(reader);
        Assertions.assertEquals(1, lineNumber);
        
        reader.readLine(); // Empty Line
        lineNumber = invokeGetLineNumber(reader);
        Assertions.assertEquals(1, lineNumber);
        
        reader.readLine(); // Line 3
        lineNumber = invokeGetLineNumber(reader);
        Assertions.assertEquals(2, lineNumber);
        
        reader.readLine(); // Line 4
        lineNumber = invokeGetLineNumber(reader);
        Assertions.assertEquals(3, lineNumber);
    }

    private int invokeGetLineNumber(ExtendedBufferedReader reader) throws Exception {
        Field lineCounterField = ExtendedBufferedReader.class.getDeclaredField("lineCounter");
        lineCounterField.setAccessible(true);
        return (int) lineCounterField.get(reader);
    }
}