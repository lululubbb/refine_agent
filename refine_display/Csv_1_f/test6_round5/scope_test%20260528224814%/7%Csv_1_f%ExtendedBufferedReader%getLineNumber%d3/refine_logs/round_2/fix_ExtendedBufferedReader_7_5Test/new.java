package org.apache.commons.csv;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.Reader;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import java.io.StringReader;
import java.lang.reflect.Field;
import java.lang.reflect.Method;

class ExtendedBufferedReader_7_5Test {

    @Test
    void testgetLineNumber_initialState() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(""));

        int lineNumber = invokeGetLineNumber(reader);
        
        Assertions.assertEquals(0, lineNumber);
    }

    @Test
    void testgetLineNumber_afterReadingLine() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader("First line\nSecond line"));

        reader.readLine(); // This would typically increase the line counter

        int lineNumber = invokeGetLineNumber(reader);
        
        Assertions.assertEquals(1, lineNumber);
    }

    @Test
    void testgetLineNumber_afterMultipleReads() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader("Line 1\nLine 2\nLine 3"));

        reader.readLine();
        reader.readLine();

        int lineNumber = invokeGetLineNumber(reader);
        
        Assertions.assertEquals(2, lineNumber);
    }

    @Test
    void testgetLineNumber_emptyString() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(""));

        int lineNumber = invokeGetLineNumber(reader);
        
        Assertions.assertEquals(0, lineNumber);
    }

    @Test
    void testgetLineNumber_singleLineWithNewline() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader("Single line\n"));

        reader.readLine();

        int lineNumber = invokeGetLineNumber(reader);
        
        Assertions.assertEquals(1, lineNumber);
    }

    @Test
    void testgetLineNumber_multipleLinesEndingWithNewline() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader("Line 1\nLine 2\nLine 3\n"));

        reader.readLine();
        reader.readLine();
        reader.readLine();

        int lineNumber = invokeGetLineNumber(reader);
        
        Assertions.assertEquals(3, lineNumber);
    }

    @Test
    void testgetLineNumber_noNewlineAtEnd() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader("Line 1\nLine 2"));

        reader.readLine();
        reader.readLine();

        int lineNumber = invokeGetLineNumber(reader);
        
        Assertions.assertEquals(2, lineNumber);
    }

    @Test
    void testgetLineNumber_afterReadingAllLines() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader("Line 1\nLine 2\nLine 3"));

        reader.readLine();
        reader.readLine();
        reader.readLine();
        // After reading all lines, the line number should still reflect the last read line.
        int lineNumber = invokeGetLineNumber(reader);
        
        Assertions.assertEquals(3, lineNumber);
    }

    private int invokeGetLineNumber(ExtendedBufferedReader reader) throws Exception {
        Method method = ExtendedBufferedReader.class.getDeclaredMethod("getLineNumber");
        method.setAccessible(true);
        return (int) method.invoke(reader);
    }

    private void setLineCounter(ExtendedBufferedReader reader, int lineCounter) throws Exception {
        Field field = ExtendedBufferedReader.class.getDeclaredField("lineCounter");
        field.setAccessible(true);
        field.setInt(reader, lineCounter);
    }
}