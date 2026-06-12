package org.apache.commons.csv;
import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import java.util.Map;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

import java.lang.reflect.Method;
import java.util.Collections;
import java.util.HashMap;

public class CSVRecord_12_2Test {

    @Test
    public void testtoString_emptyArray() throws Exception {
        CSVRecord record = new CSVRecord(new String[]{}, new HashMap<>(), null, 0);
        String result = invokeToString(record);
        Assertions.assertEquals("[]", result);
    }

    @Test
    public void testtoString_singleElement() throws Exception {
        CSVRecord record = new CSVRecord(new String[]{"value1"}, new HashMap<>(), null, 1);
        String result = invokeToString(record);
        Assertions.assertEquals("[value1]", result);
    }

    @Test
    public void testtoString_multipleElements() throws Exception {
        CSVRecord record = new CSVRecord(new String[]{"value1", "value2", "value3"}, new HashMap<>(), null, 2);
        String result = invokeToString(record);
        Assertions.assertEquals("[value1, value2, value3]", result);
    }

    @Test
    public void testtoString_withNulls() throws Exception {
        CSVRecord record = new CSVRecord(new String[]{"value1", null, "value3"}, new HashMap<>(), null, 3);
        String result = invokeToString(record);
        Assertions.assertEquals("[value1, null, value3]", result);
    }

    @Test
    public void testtoString_emptyRecord() throws Exception {
        CSVRecord record = new CSVRecord(new String[]{}, new HashMap<>(), "Comment", 4);
        String result = invokeToString(record);
        Assertions.assertEquals("[]", result);
    }

    private String invokeToString(CSVRecord record) throws Exception {
        Method method = CSVRecord.class.getDeclaredMethod("toString");
        method.setAccessible(true);
        return (String) method.invoke(record);
    }
}