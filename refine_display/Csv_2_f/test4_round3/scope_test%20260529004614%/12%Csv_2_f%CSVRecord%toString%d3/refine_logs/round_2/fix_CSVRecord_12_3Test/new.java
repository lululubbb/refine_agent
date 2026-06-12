package org.apache.commons.csv;

import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import java.lang.reflect.Method;
import java.util.Collections;
import java.util.HashMap;
import java.util.Map;

public class CSVRecord_12_3Test {

    @Test
    public void testToString_emptyArray() throws Exception {
        String[] values = new String[0];
        CSVRecord record = new CSVRecord(values, Collections.emptyMap(), null, 0);
        String result = invokeToString(record);
        Assertions.assertEquals("[]", result);
    }

    @Test
    public void testToString_singleElement() throws Exception {
        String[] values = new String[]{"value1"};
        CSVRecord record = new CSVRecord(values, Collections.emptyMap(), null, 1);
        String result = invokeToString(record);
        Assertions.assertEquals("[value1]", result);
    }

    @Test
    public void testToString_multipleElements() throws Exception {
        String[] values = new String[]{"value1", "value2", "value3"};
        CSVRecord record = new CSVRecord(values, Collections.emptyMap(), null, 2);
        String result = invokeToString(record);
        Assertions.assertEquals("[value1, value2, value3]", result);
    }

    @Test
    public void testToString_withNullValues() throws Exception {
        String[] values = new String[]{"value1", null, "value3"};
        CSVRecord record = new CSVRecord(values, Collections.emptyMap(), null, 3);
        String result = invokeToString(record);
        Assertions.assertEquals("[value1, null, value3]", result);
    }

    @Test
    public void testToString_boundaryValues() throws Exception {
        String[] values = new String[1000]; // Testing a large array
        Arrays.fill(values, "value");
        CSVRecord record = new CSVRecord(values, Collections.emptyMap(), null, 4);
        String expected = Arrays.toString(values);
        String result = invokeToString(record);
        Assertions.assertEquals(expected, result);
    }

    @Test
    public void testToString_specialCharacters() throws Exception {
        String[] values = new String[]{"value1", "value,2", "value\n3"};
        CSVRecord record = new CSVRecord(values, Collections.emptyMap(), null, 5);
        String expected = "[value1, value,2, value\n3]";
        String result = invokeToString(record);
        Assertions.assertEquals(expected, result);
    }

    private String invokeToString(CSVRecord record) throws Exception {
        Method method = CSVRecord.class.getDeclaredMethod("toString");
        method.setAccessible(true);
        return (String) method.invoke(record);
    }
}