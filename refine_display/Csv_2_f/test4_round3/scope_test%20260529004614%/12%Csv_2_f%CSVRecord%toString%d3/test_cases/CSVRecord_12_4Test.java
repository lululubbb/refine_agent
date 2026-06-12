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

public class CSVRecord_12_4Test {

    private static final String EMPTY_STRING_REPRESENTATION = "[]";
    private static final String NULL_STRING_REPRESENTATION = "null";

    @Test
    public void testtoString_emptyValues() throws Exception {
        String[] values = {};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(values, mapping, null, 1);
        String result = invokeToString(record);
        Assertions.assertEquals(EMPTY_STRING_REPRESENTATION, result);
    }

    @Test
    public void testtoString_singleValue() throws Exception {
        String[] values = {"value1"};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(values, mapping, null, 1);
        String result = invokeToString(record);
        Assertions.assertEquals("[value1]", result);
    }

    @Test
    public void testtoString_multipleValues() throws Exception {
        String[] values = {"value1", "value2", "value3"};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(values, mapping, null, 1);
        String result = invokeToString(record);
        Assertions.assertEquals("[value1, value2, value3]", result);
    }

    @Test
    public void testtoString_withNullValue() throws Exception {
        String[] values = {"value1", null, "value3"};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(values, mapping, null, 1);
        String result = invokeToString(record);
        Assertions.assertEquals("[value1, null, value3]", result);
    }

    @Test
    public void testtoString_withAllNullValues() throws Exception {
        String[] values = {null, null, null};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(values, mapping, null, 1);
        String result = invokeToString(record);
        Assertions.assertEquals("[null, null, null]", result);
    }

    @Test
    public void testtoString_boundaryValues() throws Exception {
        String[] values = {""}; // Test with an empty string
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(values, mapping, null, 1);
        String result = invokeToString(record);
        Assertions.assertEquals("[ ]", result); // Expecting space between brackets
    }

    private String invokeToString(CSVRecord record) throws Exception {
        Method method = CSVRecord.class.getDeclaredMethod("toString");
        method.setAccessible(true);
        return (String) method.invoke(record);
    }
}